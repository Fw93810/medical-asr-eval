"""Paired bootstrap between ASR runs on the test set, resampling consultations.

Three metrics on one channel (default: mixed), each a ratio of sums over the
consultations in the sample:
  * wer_corrected: (S + D + I) / reference words, from results/equiv/<run>/wer.csv
  * medical_term_error_rate: substituted or deleted medical-term words / medical-term
    words in the reference (classes as in error_composition.py, scispaCy)
  * clinical_negation_lost: clinical negations deleted or replaced by a non-negation /
    clinical negations in the reference (analyze_negations.py)

The same resampled consultation sets are used for every run, so each pair's
difference is paired. Writes <out>/pairwise.csv (every pair, both orders not
repeated), <out>/per_run.csv (each run's value with its own 95% interval) and
<out>/per_consultation.csv.

Usage:
  python -I scripts/bootstrap_asr.py --data data/prepared_test47 --runs test47-qwen3-asr-1.7b test47-vad-nocond ...
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from itertools import combinations

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # -I drops the script dir from sys.path
from error_composition import classify, reference  # noqa: E402

METRICS = ("wer_corrected", "medical_term_error_rate", "clinical_negation_lost")


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def medical_ref_counts(data, cids, cond):
    import spacy
    nlp = spacy.load("en_core_sci_sm")
    counts = {}
    for cid in cids:
        with open(os.path.join(data, cid, "utterances.json")) as f:
            utts = sorted(json.load(f)["utterances"], key=lambda u: u["start"])
        n = 0
        for r in reference(utts, nlp):
            if cond == "mixed" or r["speaker"] == cond:
                n += sum(classify(r["words"], k, k in r["medical"], k in r["proper"]) == "medical_term"
                         for k in range(len(r["words"])))
        counts[cid] = n
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--condition", default="mixed")
    ap.add_argument("--equiv-root", default="results/equiv")
    ap.add_argument("--composition", default="results/test47/error_composition/error_ops.csv")
    ap.add_argument("--negations", default="results/test47/negations/negation_words.csv")
    ap.add_argument("--out", default="results/test47/bootstrap")
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    cond = args.condition

    cids = sorted(d for d in os.listdir(args.data) if os.path.isfile(os.path.join(args.data, d, "utterances.json")))
    # num[metric][run][cid], den[metric][run][cid]
    num = {m: defaultdict(lambda: defaultdict(int)) for m in METRICS}
    den = {m: defaultdict(lambda: defaultdict(int)) for m in METRICS}

    for run in args.runs:
        for r in read_csv(os.path.join(args.equiv_root, run, "wer.csv")):
            if r["condition"] == cond:
                num["wer_corrected"][run][r["id"]] = int(r["substitutions"]) + int(r["deletions"]) + int(r["insertions"])
                den["wer_corrected"][run][r["id"]] = int(r["ref_words"])

    med = medical_ref_counts(args.data, cids, cond)
    runs = set(args.runs)
    for o in read_csv(args.composition):
        if o["run"] in runs and o["condition"] == cond and o["cls"] == "medical_term" and o["op"] != "ins":
            num["medical_term_error_rate"][o["run"]][o["id"]] += 1
    for run in args.runs:
        for cid in cids:
            den["medical_term_error_rate"][run][cid] = med[cid]

    for r in read_csv(args.negations):
        if r["run"] in runs and r["condition"] == cond and r["class"] == "negation_clinical":
            den["clinical_negation_lost"][r["run"]][r["id"]] += 1
            num["clinical_negation_lost"][r["run"]][r["id"]] += r["negation_kept"] != "1"

    for run in args.runs:
        missing = [c for c in cids if c not in den["wer_corrected"][run]]
        assert not missing, f"{run}: no {cond} result for {missing[:3]}"

    # arrays: metric -> run -> (numerators, denominators) over cids
    arr = {m: {run: (np.array([num[m][run][c] for c in cids], float), np.array([den[m][run][c] for c in cids], float))
               for run in args.runs} for m in METRICS}
    rng = np.random.default_rng(args.seed)
    idx = rng.integers(0, len(cids), size=(args.boot, len(cids)))
    counts = np.stack([np.bincount(row, minlength=len(cids)) for row in idx])  # boot x cids, weights

    point, boot = {}, {}
    for m in METRICS:
        for run in args.runs:
            n, d = arr[m][run]
            point[(m, run)] = n.sum() / d.sum()
            boot[(m, run)] = (counts @ n) / (counts @ d)

    per_run = []
    for m in METRICS:
        for run in args.runs:
            lo, hi = np.percentile(boot[(m, run)], [2.5, 97.5])
            per_run.append({"metric": m, "condition": cond, "run": run, "value": round(point[(m, run)], 4),
                            "ci95_low": round(lo, 4), "ci95_high": round(hi, 4)})
    with open(os.path.join(args.out, "per_run.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(per_run[0].keys()))
        w.writeheader()
        w.writerows(per_run)

    rows = []
    for a, b in combinations(args.runs, 2):
        for m in METRICS:
            diff = boot[(m, a)] - boot[(m, b)]
            lo, hi = np.percentile(diff, [2.5, 97.5])
            rows.append({"metric": m, "condition": cond, "run_a": a, "run_b": b,
                         "a": round(point[(m, a)], 4), "b": round(point[(m, b)], 4),
                         "diff_a_minus_b": round(point[(m, a)] - point[(m, b)], 4),
                         "ci95_low": round(lo, 4), "ci95_high": round(hi, 4),
                         "excludes_zero": bool(lo > 0 or hi < 0),
                         "share_boot_a_better": round(float((diff < 0).mean()), 4)})
    with open(os.path.join(args.out, "pairwise.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(args.out, "per_consultation.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "run", "id", "errors", "reference"])
        for m in METRICS:
            for run in args.runs:
                n, d = arr[m][run]
                w.writerows([m, run, c, int(x), int(y)] for c, x, y in zip(cids, n, d))

    print(f"{len(cids)} consultations, {args.boot} resamples, condition {cond}; reference totals: "
          + ", ".join(f"{m} {int(arr[m][args.runs[0]][1].sum())}" for m in METRICS))
    for r in rows:
        if r["run_a"] == args.runs[0]:
            print(f"{r['metric']:<24} {r['run_a']} - {r['run_b']}: {100 * r['diff_a_minus_b']:+.2f} "
                  f"[{100 * r['ci95_low']:+.2f}, {100 * r['ci95_high']:+.2f}]")


if __name__ == "__main__":
    main()
