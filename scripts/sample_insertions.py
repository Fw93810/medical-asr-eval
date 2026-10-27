"""Draw a random sample of insertion runs to listen to and label by hand.

Some "insertions" are not ASR errors: the human reference skipped words that
were really said, or the words belong to the other speaker leaking into the
channel. Listening to a random sample estimates how often that happens.

Reads <results>/insertions.csv (from evaluate.py) and writes a CSV (UTF-8 with
BOM, so Excel shows it correctly) with an empty `label` column and a link that
opens the viewer at that track and time. Labels to use:
  ref_missing    the words were really said; the reference left them out
  crosstalk      the other speaker's words leaking into this channel
  hallucination  nothing like this was said
  misaligned     the words are in the reference, just placed elsewhere
  unclear        cannot tell

Usage:
  python -I scripts/sample_insertions.py --results results/test47-vad-nocond --n 40 \
      --out results/test47/listening_sample.csv --viewer http://127.0.0.1:8765/results/viewer-test47/
"""
import argparse
import csv
import os
import random


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True, help="evaluate.py result folder")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--viewer", default="http://127.0.0.1:8765/results/viewer/")
    args = ap.parse_args()

    with open(os.path.join(args.results, "insertions.csv"), newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    sample = random.Random(args.seed).sample(rows, min(args.n, len(rows)))
    sample.sort(key=lambda r: (r["id"], r["condition"], float(r["t_approx_s"])))

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["n", "id", "condition", "t_s", "n_words", "inserted", "hyp_context", "ref_context",
                    "link", "label", "note"])
        for i, r in enumerate(sample, 1):
            t = float(r["t_approx_s"])
            link = f"{args.viewer}#id={r['id']}&cond={r['condition']}&t={t}"
            w.writerow([i, r["id"], r["condition"], t, r["n_words"], r["inserted"], r["hyp_context"],
                        r["ref_context"], link, "", ""])
    print(f"sampled {len(sample)} of {len(rows)} insertion runs -> {args.out}")


if __name__ == "__main__":
    main()
