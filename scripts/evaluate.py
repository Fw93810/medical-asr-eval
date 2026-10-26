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
            "sorry", "thank", "thanks", "good", "fine", "hello", "hi", "mean", "know", "like"}


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
        hyp_words, hyp_times = [], []
        for seg in hyp["segments"]:
            ws = norm_words(seg["text"])
            hyp_words += ws
            hyp_times += [seg["start"]] * len(ws)

        if not hyp_words:  # jiwer needs non-empty strings
            hyp_words, hyp_times = ["<empty>"], [0.0]
        out = jiwer.process_words(" ".join(ref_words), " ".join(hyp_words))

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

    write("wer.csv", rows)
    write("summary.csv", summary)
    write("insertions.csv", ins_rows)
    write("missed_terms.csv", miss_rows)
    for s in summary:
        print(s)


if __name__ == "__main__":
    main()
