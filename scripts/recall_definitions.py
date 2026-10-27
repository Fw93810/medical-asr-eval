"""Fact recall under the two definitions used in the reports, for any judged folders.

  recall           present / all clinician facts
  recall_stated    present / facts that were said in the consultation (facts_stated.csv
                   status "stated"; "partly" and "not_stated" are left out)

Each folder is reported on all its consultations and, with --ids-file, on that subset,
so runs judged on different consultation sets can be compared on the same set.

With --regen A B --regen-out FILE it also compares two generations of the same
notes (same model and source, e.g. generated on two GPUs): share of fact labels that
change, and the paired recall difference B - A with a bootstrap interval over
consultations, on all facts and on stated facts. This is the regeneration noise floor.

Usage:
  python -I scripts/recall_definitions.py --stated results/notes/test47/facts_stated.csv \
      --ids-file results/notes/test47/grid_ids.txt --source human \
      --judged test47=results/notes/test47 grid-14b=results/notes/grid/qwen3-14b \
      --regen results/notes/test47 results/notes/grid/qwen3-14b --regen-out results/notes/grid/regeneration_noise.csv
"""
import argparse
import csv
import random


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stated", required=True)
    ap.add_argument("--judged", nargs="+", required=True, help="name=folder with fact_labels.csv")
    ap.add_argument("--source", default="human")
    ap.add_argument("--ids-file")
    ap.add_argument("--regen", nargs=2, metavar=("A", "B"), help="two judged folders with the same notes regenerated")
    ap.add_argument("--regen-out")
    ap.add_argument("--boot", type=int, default=10000)
    args = ap.parse_args()

    stated = {(r["id"], int(r["n"])): r["status"] for r in read_csv(args.stated)}
    subset = set(open(args.ids_file).read().split()) if args.ids_file else None
    print("| run | consultations | facts | recall | stated facts | recall on stated facts |")
    print("|---|---|---|---|---|---|")
    for spec in args.judged:
        name, folder = spec.split("=", 1)
        rows = [r for r in read_csv(f"{folder}/fact_labels.csv") if r["source"] == args.source]
        for label, rs in (("all", rows), ("subset", [r for r in rows if subset and r["id"] in subset])):
            if not rs:
                continue
            st = [r for r in rs if stated[(r["id"], int(r["n"]))] == "stated"]
            rec = sum(r["label"] == "present" for r in rs) / len(rs)
            rec_st = sum(r["label"] == "present" for r in st) / len(st)
            print(f"| {name} ({label}) | {len({r['id'] for r in rs})} | {len(rs)} | {100 * rec:.1f}% | "
                  f"{len(st)} | {100 * rec_st:.1f}% |")

    if args.regen:
        lab = [{(r["id"], int(r["n"])): r["label"] for r in read_csv(f"{d}/fact_labels.csv")
                if r["source"] == args.source and (not subset or r["id"] in subset)} for d in args.regen]
        out = []
        for facts in ("all", "stated"):
            keys = sorted(k for k in lab[0] if k in lab[1] and (facts == "all" or stated[k] == "stated"))
            per = {}
            for k in keys:
                d = per.setdefault(k[0], [0, 0, 0])
                d[0] += 1
                d[1] += lab[0][k] == "present"
                d[2] += lab[1][k] == "present"
            ids = sorted(per)
            diff = lambda s: (sum(per[i][2] for i in s) - sum(per[i][1] for i in s)) / sum(per[i][0] for i in s)
            rng = random.Random(0)
            boots = sorted(diff([rng.choice(ids) for _ in ids]) for _ in range(args.boot))
            out.append({"facts": facts, "consultations": len(ids), "n_facts": len(keys),
                        "label_changed_rate": round(sum(lab[0][k] != lab[1][k] for k in keys) / len(keys), 4),
                        "present_to_not": sum(lab[0][k] == "present" != lab[1][k] for k in keys),
                        "not_to_present": sum(lab[0][k] != "present" == lab[1][k] for k in keys),
                        "recall_diff": round(diff(ids), 4),
                        "recall_diff_ci95": "%.4f..%.4f" % (boots[int(0.025 * args.boot)],
                                                            boots[int(0.975 * args.boot) - 1])})
            print(out[-1])
        if args.regen_out:
            with open(args.regen_out, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
                w.writeheader()
                w.writerows(out)


if __name__ == "__main__":
    main()
