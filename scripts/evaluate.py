"""Evaluate ASR outputs against PriMock57 references.

For every <hyp>/<cid>/<condition>.json (from transcribe.py) and the matching
<data>/<cid>/ref_<condition>.txt (from prep_data.py):

  * WER with jiwer, after Whisper's English text normaliser (lower-case,
    punctuation removed, fillers like "um"/"uh" removed, numbers and British
    spellings standardised). Texts are normalised utterance-by-utterance /
    segment-by-segment so hypothesis words keep their timestamps.
  * Medical-term recall = fraction of distinct medical terms in the reference
    that also occur (as a contiguous word sequence) in the hypothesis.
    Terms come from scispaCy en_core_sci_sm entities if that model is
    installed, otherwise from the hand-written lexicon scripts/medical_terms.txt
    (see --terms). The extractor used is recorded in the CSV.
  * Insertions: runs of hypothesis words that the jiwer alignment marks as
    "insert" (no reference word). Long runs are a cheap hallucination signal.
  * Overlap split: errors inside vs outside the time spans where doctor and
    patient utterances overlap (from utterances.json). Word times are
    approximate: each utterance's / segment's words are spread evenly over its
    span. Substitutions and deletions are placed by the reference word's time,
    insertions by the hypothesis word's time; rates are per reference word in
    the same region.

Writes to --results:
  wer.csv           one row per consultation x condition
  summary.csv       one row per condition (corpus WER = total errors / total ref words)
  insertions.csv    every insertion run with its timestamp and context
  missed_terms.csv  reference medical terms not found in the hypothesis

Usage:
  python -I scripts/evaluate.py --data data/prepared_3min --hyp outputs/fw-base --results results/fw-base
"""
import argparse
import csv
import glob
import json
import os
import re
from collections import defaultdict

import jiwer
from whisper_normalizer.english import EnglishTextNormalizer

NORM = EnglishTextNormalizer()
HERE = os.path.dirname(os.path.abspath(__file__))
# single-word scispaCy "entities" that are too generic to count as medical terms
SCI_STOP = {"yeah", "okay", "ok", "right", "thing", "things", "time", "times", "day", "days",
            "week", "weeks", "morning", "today", "bit", "lot", "sort", "kind", "way", "people",
            "sorry", "thank", "thanks", "good", "fine", "hello", "hi", "mean", "know", "like",
            "i", "you", "we", "he", "she", "it", "they", "me", "my", "your"}


def norm_words(text):
    return NORM(text).split()


def load_term_extractor(choice):
    if choice in ("auto", "scispacy"):
        try:
            import spacy
            nlp = spacy.load("en_core_sci_sm")

            def extract(raw_lines):
                terms = set()
                for line in raw_lines:
                    for ent in nlp(line).ents:
                        t = " ".join(norm_words(ent.text))
                        if t and t not in SCI_STOP:
                            terms.add(t)
                return terms

            return "scispacy:en_core_sci_sm", extract
        except Exception as e:  # not installed / model missing
            if choice == "scispacy":
                raise
            print(f"scispaCy unavailable ({type(e).__name__}: {e}); using lexicon fallback")

    lexicon = set()
    with open(os.path.join(HERE, "medical_terms.txt")) as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if line:
                t = " ".join(norm_words(line))
                if t:
                    lexicon.add(t)

    def extract(raw_lines):
        words = norm_words(" ".join(raw_lines))
        return {t for t in lexicon if contains(words, t.split())}

    return f"lexicon:medical_terms.txt({len(lexicon)})", extract


def contains(words, term):
    """True if `term` (list of words) occurs contiguously in `words`; last word may carry a plural 's'."""
    n = len(term)
    for i in range(len(words) - n + 1):
        if words[i:i + n - 1] == term[:-1] and words[i + n - 1] in (term[-1], term[-1] + "s"):
            return True
    return False


def spread(n, start, end):
    """Approximate times for n words spread evenly over [start, end]."""
    end = start if end is None else end
    return [start + (k + 0.5) / n * (end - start) for k in range(n)]


def load_overlap(data_dir, cid, cond, ref_lines):
    """Overlap intervals (doctor x patient) and approximate time per reference word.

    Returns (intervals, ref_word_times), or (None, None) if utterances.json is
    missing or does not match ref_<cond>.txt line by line.
    """
    path = os.path.join(data_dir, cid, "utterances.json")
    if not os.path.isfile(path):
        return None, None
    with open(path) as f:
        utts = json.load(f)["utterances"]
    doc = [(u["start"], u["end"]) for u in utts if u["speaker"] == "doctor"]
    pat = [(u["start"], u["end"]) for u in utts if u["speaker"] == "patient"]
    intervals = sorted((max(a, c), min(b, d)) for a, b in doc for c, d in pat if max(a, c) < min(b, d))
    merged = []
    for a, b in intervals:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])

    mine = sorted((u for u in utts if cond == "mixed" or u["speaker"] == cond), key=lambda u: u["start"])
    if [u["text"].strip() for u in mine] != ref_lines:
        return None, None
    times = []
    for u in mine:
        times += spread(len(norm_words(u["text"])), u["start"], u["end"])
    return merged, times


def in_any(t, intervals):
    return any(a <= t <= b for a, b in intervals)


OV_COUNTS = ("overlap_s", "ref_in", "ref_out", "sub_in", "sub_out", "del_in", "del_out", "ins_in", "ins_out")


def overlap_columns(ov):
    """Counts plus per-region error rates (per reference word in that region)."""
    if ov is None:
        return {}
    cols = {f"ov_{k}": ov[k] for k in OV_COUNTS}
    for kind in ("sub", "del", "ins"):
        for region in ("in", "out"):
            n = ov[f"ref_{region}"]
            cols[f"{kind}_rate_{region}"] = round(ov[f"{kind}_{region}"] / n, 4) if n else ""
    return cols


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/prepared")
    ap.add_argument("--hyp", required=True, help="output folder of transcribe.py")
    ap.add_argument("--results", required=True)
    ap.add_argument("--terms", choices=["auto", "scispacy", "lexicon"], default="auto")
    ap.add_argument("--min-insert-words", type=int, default=1,
                    help="only log insertion runs with at least this many words")
    args = ap.parse_args()

    extractor_name, extract_terms = load_term_extractor(args.terms)
    os.makedirs(args.results, exist_ok=True)
    rows, ins_rows, miss_rows = [], [], []

    for hyp_path in sorted(glob.glob(os.path.join(args.hyp, "*", "*.json"))):
        with open(hyp_path) as f:
            hyp = json.load(f)
        cid, cond = hyp["id"], hyp["condition"]
        with open(os.path.join(args.data, cid, f"ref_{cond}.txt")) as f:
            ref_lines = [l.strip() for l in f if l.strip()]

        ref_words = [w for line in ref_lines for w in norm_words(line)]
        hyp_words, hyp_times, hyp_wtimes = [], [], []
        for seg in hyp["segments"]:
            ws = norm_words(seg["text"])
            hyp_words += ws
            hyp_times += [seg["start"]] * len(ws)
            hyp_wtimes += spread(len(ws), seg["start"], seg["end"])

        if not hyp_words:  # jiwer needs non-empty strings
            hyp_words, hyp_times, hyp_wtimes = ["<empty>"], [0.0], [0.0]
        out = jiwer.process_words(" ".join(ref_words), " ".join(hyp_words))

        overlaps, ref_wtimes = load_overlap(args.data, cid, cond, ref_lines)
        ov = None
        if overlaps is not None:
            ref_in = [in_any(t, overlaps) for t in ref_wtimes]
            ov = {k: 0 for k in ("ref_in", "sub_in", "del_in", "ins_in", "sub_out", "del_out", "ins_out")}
            ov["ref_in"] = sum(ref_in)
            for chunk in out.alignments[0]:
                if chunk.type == "insert":
                    for j in range(chunk.hyp_start_idx, chunk.hyp_end_idx):
                        ov["ins_in" if in_any(hyp_wtimes[j], overlaps) else "ins_out"] += 1
                elif chunk.type in ("substitute", "delete"):
                    k = "sub" if chunk.type == "substitute" else "del"
                    for i in range(chunk.ref_start_idx, chunk.ref_end_idx):
                        ov[f"{k}_in" if ref_in[i] else f"{k}_out"] += 1
            ov["ref_out"] = len(ref_words) - ov["ref_in"]
            ov["overlap_s"] = round(sum(b - a for a, b in overlaps), 1)

        for chunk in out.alignments[0]:
            if chunk.type != "insert":
                continue
            n = chunk.hyp_end_idx - chunk.hyp_start_idx
            if n < args.min_insert_words:
                continue
            a, b = chunk.hyp_start_idx, chunk.hyp_end_idx
            ins_rows.append({
                "id": cid, "condition": cond, "n_words": n,
                "segment_start_s": hyp_times[a],
                "in_overlap": "" if overlaps is None else int(in_any(hyp_wtimes[a], overlaps)),
                "inserted": " ".join(hyp_words[a:b]),
                "hyp_context": " ".join(hyp_words[max(0, a - 6):a]) + " [[" + " ".join(hyp_words[a:b])
                               + "]] " + " ".join(hyp_words[b:b + 6]),
                "ref_context": " ".join(ref_words[max(0, chunk.ref_start_idx - 6):chunk.ref_start_idx + 6]),
            })

        ref_terms = extract_terms(ref_lines)
        found = {t for t in ref_terms if contains(hyp_words, t.split())}
        for t in sorted(ref_terms - found):
            miss_rows.append({"id": cid, "condition": cond, "term": t})

        audio_min = hyp["audio_s"] / 60
        rows.append({
            "id": cid, "condition": cond, "backend": hyp["backend"], "model": hyp["model"],
            "initial_prompt": hyp.get("initial_prompt") or "",
            "ref_words": len(ref_words), "hyp_words": len(hyp_words),
            "wer": round(out.wer, 4), "substitutions": out.substitutions,
            "deletions": out.deletions, "insertions": out.insertions,
            "term_extractor": extractor_name, "ref_terms": len(ref_terms), "terms_found": len(found),
            "term_recall": round(len(found) / len(ref_terms), 4) if ref_terms else "",
            "audio_s": hyp["audio_s"], "runtime_s": hyp["runtime_s"],
            "sec_per_audio_min": round(hyp["runtime_s"] / audio_min, 2),
        })
        rows[-1].update(overlap_columns(ov))
        print(f"{cid}/{cond}: WER {out.wer:.3f}  term recall {len(found)}/{len(ref_terms)}")

    def write(name, data):
        if not data:
            return
        with open(os.path.join(args.results, name), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
            w.writeheader()
            w.writerows(data)

    by_cond = defaultdict(list)
    for r in rows:
        by_cond[r["condition"]].append(r)
    summary = []
    for cond, rs in by_cond.items():
        errs = sum(r["substitutions"] + r["deletions"] + r["insertions"] for r in rs)
        nref = sum(r["ref_words"] for r in rs)
        terms, found = sum(r["ref_terms"] for r in rs), sum(r["terms_found"] for r in rs)
        audio, runtime = sum(r["audio_s"] for r in rs), sum(r["runtime_s"] for r in rs)
        summary.append({
            "condition": cond, "model": rs[0]["model"], "n_consultations": len(rs),
            "audio_min": round(audio / 60, 2), "ref_words": nref,
            "corpus_wer": round(errs / nref, 4),
            "substitutions": sum(r["substitutions"] for r in rs),
            "deletions": sum(r["deletions"] for r in rs),
            "insertions": sum(r["insertions"] for r in rs),
            "term_recall_pooled": round(found / terms, 4) if terms else "",
            "sec_per_audio_min": round(runtime / (audio / 60), 2),
        })
        if all("ov_ref_in" in r for r in rs):
            summary[-1].update(overlap_columns({k: sum(r[f"ov_{k}"] for r in rs) for k in OV_COUNTS}))

    write("wer.csv", rows)
    write("summary.csv", summary)
    write("insertions.csv", ins_rows)
    write("missed_terms.csv", miss_rows)
    for s in summary:
        print(s)


if __name__ == "__main__":
    main()
