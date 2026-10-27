"""Who and what gets dropped when doctor and patient talk at the same time?

For every reference word that falls inside a doctor-patient overlap span, this
compares two transcriptions of the same consultation:
  * mixed:     <hyp>/<cid>/mixed.json  aligned against both speakers' words
  * separated: <hyp>/<cid>/{doctor,patient}.json aligned against that speaker's words
Each reference word is tracked by (utterance, position), so the same word gets
an outcome (correct / substitution / deletion) in both conditions. The extra
deletions caused by mixing are then broken down by:
  speaker       doctor / patient
  word_class    backchannel, function, content, negation_clinical,
                negation_discourse (fixed lists and a rule, see word_class)
  role          "came_in": the word's utterance started while the other speaker
                was already talking; "holding": the other speaker came in on it
  level         "quieter"/"louder": the word's channel RMS vs the other channel
                over that overlap span (dB, from doctor.wav / patient.wav)

Word times are approximate (each utterance's words spread evenly over it), as
in evaluate.py.

Writes to --out:
  overlap_words.csv          one row per reference word inside an overlap span
  overlap_breakdown.csv      deletion rate mixed vs separated per category
  dropped_content_words.csv  content words and clinical negations correct when separated but
                             deleted when mixed, with times, for listening

Usage:
  python -I scripts/analyze_overlap.py --data data/prepared_full10 --hyp outputs/full10-vad-nocond --out results/full10/overlap
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # -I drops the script dir from sys.path
import jiwer  # noqa: E402
from evaluate import in_any, norm_words, spread  # noqa: E402

# Fixed word classes (after Whisper normalisation). Negations are kept apart from
# backchannels on purpose: "no" can be an answer that matters ("no allergies").
BACKCHANNEL = {"yeah", "yes", "yep", "yup", "okay", "ok", "right", "mm", "mhm", "hmm", "uh", "huh",
               "oh", "ah", "aha", "sure", "alright", "great", "cool", "fine", "good", "thanks", "thank",
               "sorry", "well", "hi", "hello", "bye", "absolutely", "exactly", "perfect", "lovely", "brilliant"}
NEGATION = {"no", "not", "never", "nothing", "none", "nobody", "nope", "neither", "nor", "without"}
NOT_CLINICAL_AFTER_NEGATION = {"", "problem", "problems", "worries", "worry"}  # "no problem", "no worries"
FUNCTION = {
    "a", "an", "the", "and", "or", "but", "so", "if", "then", "than", "because", "as", "that", "this",
    "these", "those", "there", "here", "it", "its", "i", "me", "my", "mine", "you", "your", "yours",
    "we", "us", "our", "he", "him", "his", "she", "her", "they", "them", "their", "what", "which",
    "who", "whom", "whose", "when", "where", "why", "how", "is", "am", "are", "was", "were", "be",
    "been", "being", "do", "does", "did", "have", "has", "had", "will", "would", "shall", "should",
    "can", "could", "may", "might", "must", "of", "to", "in", "on", "at", "by", "for", "with", "from",
    "up", "down", "out", "about", "into", "over", "after", "before", "just", "like", "kind", "sort",
    "really", "very", "quite", "also", "too", "any", "some", "all", "any", "much", "many", "more",
    "know", "mean", "think", "get", "got", "go", "going", "gonna", "let", "say", "said", "see",
}


def word_class(ws, k):
    """Class of ws[k] given its utterance's words ws.

    A negation counts as clinical when the next word of the same utterance is a
    content word ("no fever", "no allergies", "not anymore", "nothing else");
    otherwise it is a discourse marker ("no, okay", "no no", "no problem").
    Punctuation is gone after normalisation, so "No. And ..." and "No and ..."
    look the same. This is a rule of thumb; the label is written to
    overlap_words.csv so it can be checked by hand.
    """
    w = ws[k]
    if w in NEGATION:
        nxt = ws[k + 1] if k + 1 < len(ws) else ""
        clinical = (nxt not in NEGATION and base_class(nxt) == "content"
                    and nxt not in NOT_CLINICAL_AFTER_NEGATION)
        return "negation_clinical" if clinical else "negation_discourse"
    return base_class(w)


def base_class(w):
    if w in BACKCHANNEL:
        return "backchannel"
    if w in FUNCTION:
        return "function"
    return "content"


def outcomes(ref_keys, ref_words, hyp_segments):
    """Align ref words to the hypothesis; return {ref_key: 'eq'|'sub'|'del'}."""
    hyp = [w for s in hyp_segments for w in norm_words(s["text"])] or ["<empty>"]
    out = jiwer.process_words(" ".join(ref_words), " ".join(hyp))
    res = {}
    for c in out.alignments[0]:
        if c.type == "insert":
            continue
        op = {"equal": "eq", "substitute": "sub", "delete": "del"}[c.type]
        for i in range(c.ref_start_idx, c.ref_end_idx):
            res[ref_keys[i]] = op
    return res


def db(x):
    return 10 * np.log10(np.mean(x ** 2) + 1e-12)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--hyp", required=True, help="transcribe.py output with doctor, patient and mixed")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    rows = []
    for cid in sorted(os.listdir(args.hyp)):
        paths = {c: os.path.join(args.hyp, cid, f"{c}.json") for c in ("doctor", "patient", "mixed")}
        if not all(os.path.isfile(p) for p in paths.values()):
            continue
        hyps = {c: json.load(open(p))["segments"] for c, p in paths.items()}
        utts = sorted(json.load(open(os.path.join(args.data, cid, "utterances.json")))["utterances"],
                      key=lambda u: u["start"])
        audio = {c: sf.read(os.path.join(args.data, cid, f"{c}.wav"))[0] for c in ("doctor", "patient")}
        sr = sf.info(os.path.join(args.data, cid, "doctor.wav")).samplerate

        # per-word reference table: key = (utterance index, word index)
        words = {}
        for ui, u in enumerate(utts):
            ws = norm_words(u["text"])
            for k, (w, t) in enumerate(zip(ws, spread(len(ws), u["start"], u["end"]))):
                words[(ui, k)] = {"word": w, "t": t, "speaker": u["speaker"], "ui": ui,
                                  "class": word_class(ws, k)}

        def keys_for(speakers):
            ks = [k for k in sorted(words) if words[k]["speaker"] in speakers]
            return ks, [words[k]["word"] for k in ks]

        ks, ws = keys_for({"doctor", "patient"})
        mixed = outcomes(ks, ws, hyps["mixed"])
        sep = {}
        for spk in ("doctor", "patient"):
            ks, ws = keys_for({spk})
            sep.update(outcomes(ks, ws, hyps[spk]))

        for key, info in words.items():
            u = utts[info["ui"]]
            others = [v for v in utts if v["speaker"] != u["speaker"]
                      and max(u["start"], v["start"]) < min(u["end"], v["end"])]
            spans = [(max(u["start"], v["start"]), min(u["end"], v["end"]), v) for v in others]
            hit = [(a, b, v) for a, b, v in spans if a <= info["t"] <= b]
            if not hit:
                continue
            a, b, v = hit[0]
            seg = slice(int(a * sr), max(int(b * sr), int(a * sr) + 1))
            other = "patient" if u["speaker"] == "doctor" else "doctor"
            rel = db(audio[u["speaker"]][seg]) - db(audio[other][seg])
            rows.append({
                "id": cid, "t": round(info["t"], 2), "speaker": u["speaker"], "word": info["word"],
                "word_class": info["class"],
                "role": "came_in" if u["start"] > v["start"] else "holding",
                "rel_level_db": round(rel, 1), "level": "quieter" if rel < 0 else "louder",
                "utt_words": len(norm_words(u["text"])),
                "mixed": mixed.get(key, "?"), "separated": sep.get(key, "?"),
                "utterance": u["text"],
            })

    def write(name, data):
        with open(os.path.join(args.out, name), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
            w.writeheader()
            w.writerows(data)

    write("overlap_words.csv", rows)

    breakdown = []
    for dim in ("all", "speaker", "word_class", "role", "level"):
        groups = defaultdict(list)
        for r in rows:
            groups["all" if dim == "all" else r[dim]].append(r)
        for val, rs in sorted(groups.items()):
            n = len(rs)
            d_mix = sum(r["mixed"] == "del" for r in rs) / n
            d_sep = sum(r["separated"] == "del" for r in rs) / n
            breakdown.append({"dimension": dim, "value": val, "ref_words": n,
                              "del_rate_separated": round(d_sep, 4), "del_rate_mixed": round(d_mix, 4),
                              "extra_del_points": round(100 * (d_mix - d_sep), 1),
                              "share_of_extra_dels": ""})
    # which categories the extra (mixing-only) deletions consist of
    extra = [r for r in rows if r["mixed"] == "del" and r["separated"] != "del"]
    for b in breakdown:
        if b["dimension"] != "all":
            b["share_of_extra_dels"] = round(sum(r[b["dimension"]] == b["value"] for r in extra) / len(extra), 3)
    write("overlap_breakdown.csv", breakdown)

    dropped = [r for r in extra if r["word_class"] in ("content", "negation_clinical") and r["separated"] == "eq"]
    write("dropped_content_words.csv", sorted(dropped, key=lambda r: (r["id"], r["t"])))

    print(f"{len(rows)} reference words inside overlap spans; {len(extra)} deleted only when mixed; "
          f"{len(dropped)} of those are content words or clinical negations recognised correctly when separated")
    for b in breakdown:
        print(f"{b['dimension']:>10} {b['value']:<12} n={b['ref_words']:<5} del sep {b['del_rate_separated']:.1%}"
              f" -> mixed {b['del_rate_mixed']:.1%}  (+{b['extra_del_points']} pts, share {b['share_of_extra_dels']})")


if __name__ == "__main__":
    main()
