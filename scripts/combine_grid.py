"""Combine the note grid (generation model x transcript source) into one table.

Each generation model was judged in its own folder (judge_notes.py --out
results/notes/grid/<model>). This merges their fact_labels.csv into
<out>/all/fact_labels.csv with sources named "<model>/<source>", so
compare_notes.py can compare across models (same consultation, same facts), and
writes <out>/grid_summary.csv and <out>/grid.md: per cell, fact recall,
contradicted facts, extra claims per note.

Usage:
  python -I scripts/combine_grid.py --grid results/notes/grid --models qwen3-14b qwen3.8-27b gpt-oss-120b
  python -I scripts/compare_notes.py --judged results/notes/grid/all --pairs \
      qwen3-14b/human:qwen3.8-27b/human ...
"""
import argparse
import csv
import os

ROWS = ["human", "human_plain", "asr_mixed", "asr_mixed_qwen3asr", "human_rejudge"]
ROW_NAMES = {"human": "human transcript", "human_plain": "human transcript, normalised",
             "asr_mixed": "Whisper large-v3, mixed", "asr_mixed_qwen3asr": "Qwen3-ASR-1.7B, mixed",
             "human_rejudge": "human transcript, judged again (10 consultations)"}


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", required=True)
    ap.add_argument("--models", nargs="+", required=True)
    args = ap.parse_args()

    labels, cells = [], []
    for k, m in enumerate(args.models):
        for r in read_csv(os.path.join(args.grid, m, "fact_labels.csv")):
            labels.append({**r, "source": f"{m}/{r['source']}"})
            # all models together: the same consultation keeps its id (so the bootstrap still
            # resamples consultations), each model's facts get their own numbers
            labels.append({**r, "source": f"pooled/{r['source']}", "n": str(1000 * k + int(r["n"]))})
        summ = {r["source"]: r for r in read_csv(os.path.join(args.grid, m, "summary.csv"))}
        for row in ROWS:
            if row in summ:
                s = summ[row]
                cells.append({"model": m, "source": row, "notes": s["notes"], "recall": s["recall"],
                              "contradicted_rate": s["contradicted_rate"],
                              "negative_missing_rate": s["negative_missing_rate"],
                              "extra_contradicts_per_note": s["extra_contradicts_per_note"],
                              "extra_not_mentioned_per_note": s["extra_not_mentioned_per_note"]})
    os.makedirs(os.path.join(args.grid, "all"), exist_ok=True)
    write_csv(os.path.join(args.grid, "all", "fact_labels.csv"), labels)
    write_csv(os.path.join(args.grid, "grid_summary.csv"), cells)

    by = {(c["model"], c["source"]): c for c in cells}
    lines = ["Fact recall (contradicted facts) per cell:", "",
             "| source | " + " | ".join(args.models) + " |", "|---|" + "---|" * len(args.models)]
    for row in ROWS:
        vals = [f"{100 * float(by[(m, row)]['recall']):.1f}% ({100 * float(by[(m, row)]['contradicted_rate']):.1f}%)"
                if (m, row) in by else "" for m in args.models]
        lines.append(f"| {ROW_NAMES[row]} | " + " | ".join(vals) + " |")
    with open(os.path.join(args.grid, "grid.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
