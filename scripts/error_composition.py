"""What the WER is made of: break every ASR error down by word class, substitution
type and position, compute "denoised" error rates, and estimate how much of the
WER is not a real recognition error.

Same alignment as evaluate.py (Whisper normaliser, then jiwer). For each run
(transcribe.py output folder) and channel it labels every substitution,
deletion and insertion with:

  word class   negation_clinical, negation_discourse, number_duration,
               proper_or_drug, medical_term, backchannel, function, content
               (first match in this order). medical_term = scispaCy en_core_sci_sm
               entity in the reference; proper_or_drug = capitalised mid-sentence
               in the reference (drug brand names, people, places). Insertions are
               classed from the hypothesis word (medical / proper by the
               vocabulary seen in the references).
  sub type     number_format ("6" vs "six"), spelling_variant ("ok" vs "okay"),
               compound ("takeaway" vs "take away": one substitution plus one
               insertion or deletion), inflection (plural, tense),
               near_homophone (same Metaphone code: "no" vs "know"),
               number_value (two numbers with different values), other
  position     overlap (inside a doctor-patient overlap span), utterance
               boundary (first / last word of a reference utterance, or an
               insertion between utterances), silence (within 1 s of, or inside,
               a gap of >= 2 s in that channel's reference), unsure (inside an
               <UNSURE> span, or within 2 words of a span edge or of an <UNIN/> /
               <INAUDIBLE_SPEECH/> marker; insertions next to such a word)

"False" errors: spelling and format differences the normaliser leaves in
("ok"/"okay", "oh" which it turns into "0", "mum"/"mom", "alright"/"all right",
"6"/"six") and errors at places where the annotator marked the reference as
uncertain. The second group is an upper bound on reference errors there, not
a count of them, and is reported separately rather than subtracted. The exact
corrected WER comes from evaluate.py --equivalence; "WER without normalisation
artefacts" here is the same idea counted from the error labels.

Fillers (um, uh, mm, hmm) are removed by the Whisper normaliser before the WER
is computed, so they never count as errors; "yeah", "okay" etc. are kept and
counted as backchannel. Word times are approximate (spread evenly over each
utterance or segment), as in evaluate.py.

Writes to --out:
  error_ops.csv          one row per error with all labels
  composition.csv        per run x channel x word class: counts, shares, error rate, WER points
  substitution_types.csv per run x channel x substitution type
  substitution_pairs.csv the 30 most common substitution pairs per run (all channels)
  position.csv           per run x channel x position label: errors, share, rate
  denoised_wer.csv       WER, WER without backchannels, content-word WER, medical-term
                         and number error rates
  false_errors.csv       errors from normalisation (format, spelling, compounds) and
                         errors where the reference itself is uncertain
  summary.md             the main table

Usage (scispaCy environment):
  python -I scripts/error_composition.py --data data/prepared_test47 \
      --hyp outputs/test47-vad-nocond outputs/test47-parakeet-local --out results/test47/error_composition
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict

import jellyfish
import jiwer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # -I drops the script dir from sys.path
from analyze_overlap import BACKCHANNEL, FUNCTION, NEGATION, base_class, word_class  # noqa: E402
from evaluate import SCI_STOP, in_any, norm_words, spread  # noqa: E402

CLASSES = ["negation_clinical", "negation_discourse", "number_duration", "proper_or_drug", "medical_term",
           "backchannel", "function", "content"]
SUB_TYPES = ["number_format", "spelling_variant", "compound", "inflection", "near_homophone", "number_value",
             "other"]
NUMBER_VALUES = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
                 "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30,
                 "forty": 40, "fifty": 50, "hundred": 100, "thousand": 1000, "half": 0.5, "couple": 2, "once": 1,
                 "twice": 2, "dozen": 12, "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5}
NUMBER_WORDS = set(NUMBER_VALUES)
TIME_UNITS = {"second", "seconds", "minute", "minutes", "hour", "hours", "day", "days", "week", "weeks", "month",
              "months", "year", "years", "times", "mg", "milligrams", "kg", "degrees"}
IRREGULAR = [{"is", "was", "are", "were", "be", "been", "am"}, {"have", "has", "had"}, {"do", "does", "did"},
             {"go", "goes", "went", "gone"}, {"get", "got", "gets"}, {"say", "said", "says"},
             {"feel", "felt", "feels"}, {"take", "took", "taken", "takes"}, {"think", "thought"}]
CANON = {"okay": "ok", "k": "ok", "0": "oh", "ohh": "oh", "ooh": "oh", "mum": "mom", "mummy": "mommy",
          "towards": "toward", "till": "until", "gonna": "goingto", "wanna": "wantto", "cannot": "cannot"}
NEAR_TAG_WORDS = 2
LONG_GAP_S = 2.0
NEAR_S = 1.0


def is_number(w):
    return bool(re.fullmatch(r"\d+(st|nd|rd|th|s)?|\d+[.,]\d+", w)) or w in NUMBER_WORDS


def number_value(w):
    m = re.fullmatch(r"(\d+(?:[.,]\d+)?)(st|nd|rd|th|s)?", w)
    if m:
        return float(m.group(1).replace(",", "."))
    return NUMBER_VALUES.get(w)


def classify(words, k, medical, proper):
    """Word class of words[k]; medical / proper say whether that word was tagged so."""
    w = words[k]
    if w in NEGATION:
        return word_class(words, k)
    if is_number(w) or (w in TIME_UNITS and k > 0 and is_number(words[k - 1])):
        return "number_duration"
    if proper:
        return "proper_or_drug"
    if medical:
        return "medical_term"
    return base_class(w)


def stem(w):
    for suf in ("ing", "ies", "ied", "es", "ed", "'s", "s", "ly"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def canon(w):
    """Spelling-insensitive form: "okay"/"ok"/"o k" -> "ok", "oh"/"ohh"/"0" -> "oh" (the Whisper
    normaliser turns "oh" into "0"), "mum" -> "mom", "alright"/"all right" -> "alright"."""
    w = CANON.get(w, w).replace("-", "")
    return re.sub(r"(.)\1", r"\1", w)


def sub_type(a, b):
    if canon(a) == canon(b):
        return "spelling_variant"
    if is_number(a) and is_number(b):
        va, vb = number_value(a), number_value(b)
        return "number_format" if va is not None and va == vb else "number_value"
    if stem(a) == stem(b) or any(a in g and b in g for g in IRREGULAR):
        return "inflection"
    if jellyfish.metaphone(a) == jellyfish.metaphone(b):
        return "near_homophone"
    return "other"


def reference(utts, nlp):
    """Per utterance: normalised words with medical / proper / unsure flags."""
    out = []
    for u in utts:
        text = u["text"]
        ws = norm_words(text)
        medical = set()
        for ent in nlp(text).ents:
            ew = norm_words(ent.text)
            for s in range(len(ws) - len(ew) + 1):
                if ew and ws[s:s + len(ew)] == ew:
                    medical.update(i for i in range(s, s + len(ew))
                                   if ws[i] not in SCI_STOP and ws[i] not in FUNCTION and ws[i] not in BACKCHANNEL)
        caps = {m.group(1).lower() for m in re.finditer(r"(?<![.?!]\s)(?<!^)\b([A-Z][a-z]{2,})\b", text)}
        proper = {i for i, w in enumerate(ws) if w in caps and w not in FUNCTION and w not in BACKCHANNEL}
        # Annotator uncertainty: words inside <UNSURE> spans, and words within NEAR_TAG_WORDS of
        # a span edge or of an <UNIN/> / <INAUDIBLE_SPEECH/> marker. The pieces between tags are
        # normalised separately; if that does not reproduce the utterance's words exactly, all
        # words of a tagged utterance count as near a tag.
        label = ["clean"] * len(ws)
        if re.search(r"<UNSURE>|<UNIN/>|<INAUDIBLE_SPEECH/>", u["raw"]):
            inside, idx, marks = False, [], []
            for p in re.split(r"(</?UNSURE>|<[A-Z_]+/>)", u["raw"]):
                if p in ("<UNSURE>", "</UNSURE>") or re.fullmatch(r"<[A-Z_]+/>", p or ""):
                    marks.append(len(idx))
                    inside = p == "<UNSURE>" or (inside and p != "</UNSURE>")
                    continue
                idx += [inside] * len(norm_words(p))
            if len(idx) == len(ws):
                for i in range(len(ws)):
                    if idx[i]:
                        label[i] = "in_unsure_span"
                    elif any(m - NEAR_TAG_WORDS <= i < m + NEAR_TAG_WORDS for m in marks):
                        label[i] = "near_tag"
            else:
                label = ["near_tag"] * len(ws)
        out.append({"speaker": u["speaker"], "start": u["start"], "end": u["end"], "words": ws,
                    "times": spread(len(ws), u["start"], u["end"]), "medical": medical, "proper": proper,
                    "unsure": label})
    return out


def overlaps(utts):
    doc = [(u["start"], u["end"]) for u in utts if u["speaker"] == "doctor"]
    pat = [(u["start"], u["end"]) for u in utts if u["speaker"] == "patient"]
    return [(max(a, c), min(b, d)) for a, b in doc for c, d in pat if max(a, c) < min(b, d)]


def long_gaps(utts):
    spans = sorted((u["start"], u["end"]) for u in utts)
    gaps, end = [], 0.0
    for a, b in spans:
        if a - end >= LONG_GAP_S:
            gaps.append((end, a))
        end = max(end, b)
    return gaps


def silence_label(t, gaps, inside_ok):
    for a, b in gaps:
        if inside_ok and a < t < b:
            return "in_silence"
        if a - NEAR_S <= t <= b + NEAR_S:
            return "near_silence"
    return "not_near_silence"


def wer_of(ref, hyp):
    if not ref:
        return None
    o = jiwer.process_words(" ".join(ref), " ".join(hyp) or "<empty>")
    return (o.substitutions + o.deletions + o.insertions) / len(ref)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--hyp", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    import spacy
    nlp = spacy.load("en_core_sci_sm")

    cids = sorted(d for d in os.listdir(args.data) if os.path.isfile(os.path.join(args.data, d, "utterances.json")))
    refs, med_vocab, proper_vocab = {}, set(), set()
    for cid in cids:
        with open(os.path.join(args.data, cid, "utterances.json")) as f:
            utts = sorted(json.load(f)["utterances"], key=lambda u: u["start"])
        refs[cid] = (utts, reference(utts, nlp))
        for r in refs[cid][1]:
            med_vocab.update(r["words"][i] for i in r["medical"])
            proper_vocab.update(r["words"][i] for i in r["proper"])
    print(f"{len(cids)} consultations; reference vocabulary: {len(med_vocab)} medical, {len(proper_vocab)} proper/drug")

    ops, ref_counts, denoised = [], defaultdict(Counter), []
    for hyp_dir in args.hyp:
        run = os.path.basename(os.path.normpath(hyp_dir))
        for cond in ("doctor", "patient", "mixed"):
            tot_ref, filt = 0, defaultdict(lambda: [[], []])
            for cid in cids:
                path = os.path.join(hyp_dir, cid, f"{cond}.json")
                if not os.path.isfile(path):
                    continue
                utts, rr = refs[cid]
                mine = [r for r in rr if cond == "mixed" or r["speaker"] == cond]
                ov = overlaps(utts)
                gaps = long_gaps([u for u in utts if cond == "mixed" or u["speaker"] == cond])

                ref, rinfo = [], []
                for ui, r in enumerate(mine):
                    for k, w in enumerate(r["words"]):
                        ref.append(w)
                        rinfo.append({"cls": classify(r["words"], k, k in r["medical"], k in r["proper"]),
                                      "t": r["times"][k],
                                      "ui": ui, "boundary": ("single" if len(r["words"]) == 1 else "utt_start" if k == 0
                                                             else "utt_end" if k == len(r["words"]) - 1 else "middle"),
                                      "unsure": r["unsure"][k]})
                with open(path) as f:
                    segs = json.load(f)["segments"]
                hyp, htimes = [], []
                for s in segs:
                    ws = norm_words(s["text"])
                    hyp += ws
                    htimes += spread(len(ws), s["start"], s["end"])
                tot_ref += len(ref)
                for i, info in enumerate(rinfo):
                    ref_counts[(run, cond)][("class", info["cls"])] += 1
                    ref_counts[(run, cond)][("overlap", "in_overlap" if in_any(info["t"], ov) else "out_of_overlap")] += 1
                    ref_counts[(run, cond)][("boundary", info["boundary"])] += 1
                    ref_counts[(run, cond)][("silence", silence_label(info["t"], gaps, False))] += 1
                    ref_counts[(run, cond)][("unsure", info["unsure"])] += 1
                    ref_counts[(run, cond)][("all", "all")] += 1

                # filtered sequences for the denoised WERs
                hcls = [classify(hyp, j, hyp[j] in med_vocab, hyp[j] in proper_vocab) for j in range(len(hyp))]
                for name, keep in (("no_backchannel", lambda c: c != "backchannel"),
                                   ("content_only", lambda c: c not in ("backchannel", "function", "negation_discourse"))):
                    filt[name][0] += [w for w, info in zip(ref, rinfo) if keep(info["cls"])]
                    filt[name][1] += [w for w, c in zip(hyp, hcls) if keep(c)]

                if not hyp:
                    hyp, htimes, hcls = ["<empty>"], [0.0], ["content"]
                out = jiwer.process_words(" ".join(ref), " ".join(hyp))
                seq, anchor = [], {}  # (kind, ref index or None, hyp index or None); insertion -> next ref index
                for c in out.alignments[0]:
                    if c.type == "equal":
                        continue
                    if c.type == "insert":
                        for j in range(c.hyp_start_idx, c.hyp_end_idx):
                            anchor[len(seq)] = c.ref_start_idx
                            seq.append(("ins", None, j))
                    elif c.type == "delete":
                        seq += [("del", i, None) for i in range(c.ref_start_idx, c.ref_end_idx)]
                    else:
                        seq += [("sub", i, c.hyp_start_idx + k) for k, i in enumerate(range(c.ref_start_idx, c.ref_end_idx))]
                # compounds: "takeaway" -> "take away", "alright" -> "all right", "o k" -> "okay":
                # one substitution next to an insertion or deletion that together spell the same word
                compound = set()
                same = lambda a, b: canon(a) == canon(b)
                for x in range(len(seq) - 1):
                    (k1, i1, j1), (k2, i2, j2) = seq[x], seq[x + 1]
                    if ((k1 == "sub" and k2 == "ins" and j2 == j1 + 1 and same(ref[i1], hyp[j1] + hyp[j2])) or
                            (k1 == "sub" and k2 == "del" and i2 == i1 + 1 and same(hyp[j1], ref[i1] + ref[i2])) or
                            (k1 == "ins" and k2 == "sub" and j2 == j1 + 1 and same(ref[i2], hyp[j1] + hyp[j2])) or
                            (k1 == "del" and k2 == "sub" and i2 == i1 + 1 and same(hyp[j2], ref[i1] + ref[i2])) or
                            # "ok alright" -> "all right": two substitutions where one side's two words
                            # spell a word on the other side (the leftover word is a real deletion or
                            # insertion of a backchannel, counted with the compound)
                            (k1 == "sub" and k2 == "sub" and i2 == i1 + 1 and j2 == j1 + 1 and
                             (same(ref[i2], hyp[j1] + hyp[j2]) or same(ref[i1], hyp[j1] + hyp[j2]) or
                              same(hyp[j2], ref[i1] + ref[i2]) or same(hyp[j1], ref[i1] + ref[i2])))):
                        compound.update((x, x + 1))
                for x, (kind, i, j) in enumerate(seq):
                    if kind == "ins":
                        # "between utterances" when no reference utterance of this channel covers its time
                        t = htimes[j]
                        u_owner = next((r for r in mine if r["start"] <= t <= r["end"]), None)
                        a = anchor[x]  # the insertion sits between ref[a - 1] and ref[a]
                        near = [rinfo[i]["unsure"] for i in (a - 1, a) if 0 <= i < len(ref)]
                        row = {"op": "ins", "ref": "", "hyp": hyp[j], "cls": hcls[j], "t": round(t, 2),
                               "boundary": "between_utterances" if u_owner is None else "within_utterance",
                               "unsure": "near_tag" if any(v != "clean" for v in near) else "clean",
                               "silence": silence_label(t, gaps, True)}
                    else:
                        info = rinfo[i]
                        row = {"op": kind, "ref": ref[i], "hyp": hyp[j] if j is not None else "", "cls": info["cls"],
                               "t": round(info["t"], 2), "boundary": info["boundary"], "unsure": info["unsure"],
                               "silence": silence_label(info["t"], gaps, False)}
                    row["overlap"] = "in_overlap" if in_any(row["t"], ov) else "out_of_overlap"
                    row["sub_type"] = ("compound" if x in compound and kind == "sub" else
                                       sub_type(row["ref"], row["hyp"]) if kind == "sub" else "")
                    row["compound_part"] = int(x in compound)
                    ops.append({"run": run, "condition": cond, "id": cid, **row})

            if not tot_ref:  # channel not transcribed in this run (e.g. stress conditions: mixed only)
                continue
            wer_all = sum(1 for o in ops if o["run"] == run and o["condition"] == cond) / tot_ref
            d = {"run": run, "condition": cond, "ref_words": tot_ref, "wer": round(wer_all, 4)}
            for name, (r, h) in filt.items():
                d[f"wer_{name}"] = round(wer_of(r, h), 4)
            mine_ops = [o for o in ops if o["run"] == run and o["condition"] == cond]
            for cl, col in (("medical_term", "medical_term_error_rate"), ("number_duration", "number_error_rate"),
                            ("negation_clinical", "clinical_negation_error_rate")):
                n = ref_counts[(run, cond)][("class", cl)]
                e = sum(o["cls"] == cl and o["op"] != "ins" for o in mine_ops)
                d[col] = round(e / n, 4) if n else ""
            denoised.append(d)
            print(f"{run} {cond}: WER {d['wer']:.3f}  no backchannel {d['wer_no_backchannel']:.3f}  "
                  f"content only {d['wer_content_only']:.3f}  medical terms {d['medical_term_error_rate']}")

    def write(name, rows):
        with open(os.path.join(args.out, name), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    write("error_ops.csv", ops)
    write("denoised_wer.csv", denoised)

    groups = defaultdict(list)
    for o in ops:
        groups[(o["run"], o["condition"])].append(o)

    comp, subt, pos, false_rows = [], [], [], []
    for (run, cond), os_ in sorted(groups.items()):
        rc = ref_counts[(run, cond)]
        n_ref = rc[("all", "all")]
        n_sub = sum(o["op"] == "sub" for o in os_)
        n_del = sum(o["op"] == "del" for o in os_)
        n_ins = sum(o["op"] == "ins" for o in os_)
        for cl in CLASSES:
            c = [o for o in os_ if o["cls"] == cl]
            s, d_, i_ = (sum(o["op"] == k for o in c) for k in ("sub", "del", "ins"))
            comp.append({"run": run, "condition": cond, "word_class": cl, "ref_words": rc[("class", cl)],
                         "ref_share": round(rc[("class", cl)] / n_ref, 4),
                         "sub": s, "del": d_, "ins": i_,
                         "share_of_sub": round(s / n_sub, 4), "share_of_del": round(d_ / n_del, 4),
                         "share_of_ins": round(i_ / n_ins, 4), "share_of_errors": round(len(c) / len(os_), 4),
                         "error_rate": round(len(c) / rc[("class", cl)], 4) if rc[("class", cl)] else "",
                         "wer_points": round(100 * len(c) / n_ref, 2)})
        subs = [o for o in os_ if o["op"] == "sub"]
        for t in SUB_TYPES:
            k = sum(o["sub_type"] == t for o in subs)
            subt.append({"run": run, "condition": cond, "sub_type": t, "count": k, "share": round(k / len(subs), 4),
                         "wer_points": round(100 * k / n_ref, 2)})
        for dim, key in (("overlap", "overlap"), ("boundary", "boundary"), ("silence", "silence"), ("unsure", "unsure")):
            for val in sorted({o[key] for o in os_} | {v for (dd, v) in rc if dd == dim}):
                e = [o for o in os_ if o[key] == val]
                n = rc[(dim, val)]
                pos.append({"run": run, "condition": cond, "dimension": dim, "value": val, "errors": len(e),
                            "sub": sum(o["op"] == "sub" for o in e), "del": sum(o["op"] == "del" for o in e),
                            "ins": sum(o["op"] == "ins" for o in e), "share_of_errors": round(len(e) / len(os_), 4),
                            "ref_words": n, "error_rate": round(len(e) / n, 4) if n else ""})
        is_norm = [o["sub_type"] in ("number_format", "spelling_variant") or bool(o["compound_part"]) for o in os_]
        norm = [o for o, f in zip(os_, is_norm) if f]
        unsure = [o for o, f in zip(os_, is_norm) if not f and o["unsure"] != "clean"]
        false_rows.append({
            "run": run, "condition": cond, "wer": round(len(os_) / n_ref, 4),
            "normalisation_errors": len(norm), "normalisation_points": round(100 * len(norm) / n_ref, 2),
            "in_unsure_span": sum(o["unsure"] == "in_unsure_span" for o in unsure),
            "near_tag": sum(o["unsure"] == "near_tag" for o in unsure),
            "uncertain_reference_points": round(100 * len(unsure) / n_ref, 2),
            "wer_without_normalisation_errors": round((len(os_) - len(norm)) / n_ref, 4),
        })
    write("composition.csv", comp)
    write("substitution_types.csv", subt)
    write("position.csv", pos)
    write("false_errors.csv", false_rows)

    pairs = []
    for run in sorted({o["run"] for o in ops}):
        cnt = Counter((o["ref"], o["hyp"], o["sub_type"]) for o in ops if o["run"] == run and o["op"] == "sub")
        pairs += [{"run": run, "rank": r, "ref": a, "hyp": b, "sub_type": t, "count": n}
                  for r, ((a, b, t), n) in enumerate(cnt.most_common(30), 1)]
    write("substitution_pairs.csv", pairs)

    # summary.md: what the WER is made of
    lines = ["# What the WER is made of (test set)", ""]
    for run in sorted({o["run"] for o in ops}):
        lines += [f"## {run}", "", "WER points by word class (share of all errors in brackets):", "",
                  "| word class | " + " | ".join(c for c in ("doctor", "patient", "mixed")) + " |",
                  "|---|---|---|---|"]
        for cl in CLASSES:
            cells = []
            for cond in ("doctor", "patient", "mixed"):
                r = next((x for x in comp if x["run"] == run and x["condition"] == cond and x["word_class"] == cl), None)
                cells.append(f"{r['wer_points']:.2f} ({100 * r['share_of_errors']:.0f}%)" if r else "")
            lines.append(f"| {cl} | " + " | ".join(cells) + " |")
        tot = [next(x for x in false_rows if x["run"] == run and x["condition"] == c) for c in ("doctor", "patient", "mixed")
               if any(x["run"] == run and x["condition"] == c for x in false_rows)]
        lines += ["| **total WER** | " + " | ".join(f"**{100 * t['wer']:.2f}**" for t in tot) + " |", "",
                  "| | " + " | ".join(t["condition"] for t in tot) + " |", "|---|---|---|---|",
                  "| normalisation artefacts (points) | " + " | ".join(str(t["normalisation_points"]) for t in tot) + " |",
                  "| WER without normalisation artefacts | " + " | ".join(
                      f"{100 * t['wer_without_normalisation_errors']:.2f}" for t in tot) + " |",
                  "| errors at uncertain reference: upper bound, not subtracted (points) | " + " | ".join(
                      str(t["uncertain_reference_points"]) for t in tot) + " |"]
        for d in denoised:
            if d["run"] == run:
                lines.append(f"- {d['condition']}: WER without backchannels {100 * d['wer_no_backchannel']:.2f}, "
                             f"content-word WER {100 * d['wer_content_only']:.2f}, medical-term error rate "
                             f"{100 * d['medical_term_error_rate']:.2f}, number/duration error rate "
                             f"{100 * d['number_error_rate']:.2f}")
        lines.append("")
    with open(os.path.join(args.out, "summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
