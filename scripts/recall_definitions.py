"""Fact recall under the two definitions used in the reports, for any judged folders.

  recall           present / all clinician facts
  recall_stated    present / facts that were said in the consultation (facts_stated.csv
                   status "stated"; "partly" and "not_stated" are left out)

Each folder is reported on all its consultations and, with --ids-file, on that subset,
so runs judged on different consultation sets can be compared on the same set.

Usage:
  python -I scripts/recall_definitions.py --stated results/notes/test47/facts_stated.csv \
      --ids-file results/notes/test47/grid_ids.txt --source human \
      --judged test47=results/notes/test47 grid-14b=results/notes/grid/qwen3-14b
"""
import argparse
import csv


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stated", required=True)
    ap.add_argument("--judged", nargs="+", required=True, help="name=folder with fact_labels.csv")
    ap.add_argument("--source", default="human")
    ap.add_argument("--ids-file")
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


if __name__ == "__main__":
    main()
