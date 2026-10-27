"""Deletions in doctor-patient overlap by role, from the mixed channel alone.

For each run (transcribe.py output with mixed.json), aligns the mixed hypothesis to
the reference words (times spread over each utterance, as in evaluate.py) and,
for every reference word inside an overlap, records whether it was deleted and the
role of its speaker there (analyze_overlap.py's definition):
  came_in  the word's utterance started after the other speaker's overlapping one
  holding  the other speaker came in while this utterance was running
Unlike analyze_overlap.py this needs no separately transcribed channels, so it works
on synthesised conditions where only the mixed channel exists.

Writes <out>: one row per run with deletion rates outside overlap, inside overlap,
and inside overlap per role.

Usage:
  python -I scripts/stress_overlap_roles.py --out results/stress/full10/overlap_roles.csv \
      --runs s1_1x-whisper=data/stress/full10/s1_1x,outputs/stress/full10/s1_1x-whisper ...
"""
import argparse
import csv
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # -I drops the script dir from sys.path
from analyze_overlap import outcomes  # noqa: E402
from evaluate import norm_words, spread  # noqa: E402


def run_stats(data, hyp):
    n, d = Counter(), Counter()
    for cid in sorted(os.listdir(hyp)):
        path = os.path.join(hyp, cid, "mixed.json")
        if not os.path.isfile(path):
            continue
        segs = json.load(open(path))["segments"]
        utts = sorted(json.load(open(os.path.join(data, cid, "utterances.json")))["utterances"],
                      key=lambda u: u["start"])
        keys, words, info = [], [], {}
        for ui, u in enumerate(utts):
            ws = norm_words(u["text"])
            for k, (w, t) in enumerate(zip(ws, spread(len(ws), u["start"], u["end"]))):
                keys.append((ui, k))
                words.append(w)
                info[(ui, k)] = (ui, t)
        res = outcomes(keys, words, segs)
        for key, (ui, t) in info.items():
            u = utts[ui]
            hit = [v for v in utts if v["speaker"] != u["speaker"]
                   and max(u["start"], v["start"]) <= t <= min(u["end"], v["end"])]
            if hit:
                groups = ["in_overlap", "came_in" if u["start"] > hit[0]["start"] else "holding"]
            else:
                groups = ["out_of_overlap"]
            for g in groups + ["all"]:
                n[g] += 1
                d[g] += res.get(key) == "del"
    return n, d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True, help="name=data_dir,hyp_dir")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    rows = []
    for spec in args.runs:
        name, paths = spec.split("=", 1)
        data, hyp = paths.split(",", 1)
        n, d = run_stats(data, hyp)
        row = {"run": name}
        for g in ("all", "out_of_overlap", "in_overlap", "came_in", "holding"):
            row[f"ref_{g}"] = n[g]
            row[f"del_rate_{g}"] = round(d[g] / n[g], 4) if n[g] else ""
        rows.append(row)
        print(row)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
