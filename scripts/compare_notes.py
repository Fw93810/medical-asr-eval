"""Paired comparison of note quality: ASR-based notes vs the human-transcript note.

Reads fact_labels.csv from judge_notes.py. Every fact is judged once per source
for the same consultation, so each ASR source can be compared with the human
source fact by fact:
  * per-consultation differences in recall and contradiction rate, with a
    bootstrap 95% interval over consultations;
  * discordant facts: present in the human-transcript note but missing or
    contradicted in the ASR note ("lost"), and the reverse ("gained"). If ASR
    errors made notes worse, "lost" should clearly outnumber "gained"; if the
    two are similar, the differences are mostly the note generator's own
    variation.
Control comparisons (--pairs) put that in scale: human:human_rejudge is the
judge's own noise (same note judged twice), human:human_plain is how much the
note changes from surface form alone, human_unlabelled:asr_mixed isolates ASR
word errors from the missing speaker labels.

Writes to --out: paired_summary.csv, discordant_facts.csv

Usage:
  python -I scripts/compare_notes.py --judged results/notes/test47
  python -I scripts/compare_notes.py --judged results/notes/test47 --pairs human:human_rejudge \
      human:human_plain human:human_unlabelled human_unlabelled:asr_mixed human:asr_separated
"""
import argparse
import csv
import os
import random
from collections import defaultdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judged", required=True, help="judge_notes.py output folder")
    ap.add_argument("--baseline", default="human")
    ap.add_argument("--pairs", nargs="*", help="comparisons as baseline:source (default: --baseline "
                                               "against every other source)")
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--stated", help="facts_stated.csv: keep only facts said in the consultation (status "
                                     "'stated'); outputs get a _stated suffix")
    args = ap.parse_args()

    with open(os.path.join(args.judged, "fact_labels.csv"), newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    suffix = ""
    if args.stated:
        with open(args.stated, newline="", encoding="utf-8-sig") as f:
            said = {(r["id"], int(r["n"]) % 1000) for r in csv.DictReader(f) if r["status"] == "stated"}
        # pooled rows (combine_grid.py) number each model's facts 1000 * k + n
        rows = [r for r in rows if (r["id"], int(r["n"]) % 1000) in said]
        suffix = "_stated"
    lab = {(r["id"], r["source"], int(r["n"])): r for r in rows}
    pairs = ([tuple(p.split(":")) for p in args.pairs] if args.pairs else
             [(args.baseline, s) for s in sorted({r["source"] for r in rows} - {args.baseline})])
    ids = sorted({r["id"] for r in rows})
    rng = random.Random(args.seed)

    summary, discordant = [], []
    for base, src in pairs:
        per_id = defaultdict(lambda: [0, 0, 0, 0, 0])  # facts, present_base, present_src, contra_base, contra_src
        lost = gained = lost_neg = gained_neg = 0
        for (cid, s, n), r in lab.items():
            if s != base or (cid, src, n) not in lab:
                continue
            o = lab[(cid, src, n)]
            d = per_id[cid]
            d[0] += 1
            d[1] += r["label"] == "present"
            d[2] += o["label"] == "present"
            d[3] += r["label"] == "contradicted"
            d[4] += o["label"] == "contradicted"
            if r["label"] != o["label"] and "present" in (r["label"], o["label"]):
                kind = "lost" if r["label"] == "present" else "gained"
                neg = r["negative"] == "True"
                lost += kind == "lost"
                gained += kind == "gained"
                lost_neg += kind == "lost" and neg
                gained_neg += kind == "gained" and neg
                discordant.append({"baseline": base, "source": src, "kind": kind, "id": cid, "n": n,
                                   "fact": r["fact"],
                                   "category": r["category"], "negative": r["negative"],
                                   "baseline_label": r["label"], "source_label": o["label"],
                                   "baseline_evidence": r["evidence"], "source_evidence": o["evidence"]})

        def diffs(sample):
            f = sum(per_id[i][0] for i in sample)
            return ((sum(per_id[i][2] for i in sample) - sum(per_id[i][1] for i in sample)) / f,
                    (sum(per_id[i][4] for i in sample) - sum(per_id[i][3] for i in sample)) / f)

        pids = sorted(per_id)
        point = diffs(pids)
        boots = sorted(diffs([rng.choice(pids) for _ in pids]) for _ in range(args.boot))
        rec = sorted(b[0] for b in boots)
        con = sorted(b[1] for b in boots)
        ci = lambda xs: (xs[int(0.025 * len(xs))], xs[int(0.975 * len(xs)) - 1])
        summary.append({
            "source": src, "vs": base, "consultations": len({i for i in per_id}),
            "recall_diff": round(point[0], 4), "recall_diff_ci95": "%.4f..%.4f" % ci(rec),
            "contradicted_diff": round(point[1], 4), "contradicted_diff_ci95": "%.4f..%.4f" % ci(con),
            "facts_lost": lost, "facts_gained": gained,
            "negative_facts_lost": lost_neg, "negative_facts_gained": gained_neg,
        })

    for name, data in ((f"paired_summary{suffix}.csv", summary), (f"discordant_facts{suffix}.csv", discordant)):
        with open(os.path.join(args.judged, name), "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
            w.writeheader()
            w.writerows(data)
    for s in summary:
        print(s)


if __name__ == "__main__":
    main()
