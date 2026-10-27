"""Combine several evaluate.py result folders into one comparison table.

Reads <dir>/summary.csv and <dir>/insertions.csv from each --results folder
(the folder name is used as the run name) and writes to --out:
  comparison.csv      one row per run x condition, with error rates per reference word
  top_insertions.csv  the --top longest insertion runs across all runs
and prints both as Markdown.

Usage:
  python -I scripts/aggregate_results.py --results results/full10-* --out results/full10
"""
import argparse
import csv
import glob
import os


def read(path):
    if not os.path.isfile(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pct(x):
    return "" if x in ("", None) else f"{float(x) * 100:.1f}%"


def markdown(rows, cols):
    lines = ["| " + " | ".join(h for h, _ in cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(f(r)) for _, f in cols) + " |" for r in rows]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", nargs="+", required=True, help="evaluate.py result folders (globs ok)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--corrected-root", help="folder holding the same runs evaluated with --equivalence "
                                             "(e.g. results/equiv); adds the corrected WER next to the raw one")
    ap.add_argument("--long-run", type=int, default=10,
                    help="insertion runs with at least this many words count as long runs (loops)")
    args = ap.parse_args()

    dirs = sorted({d for pattern in args.results for d in glob.glob(pattern) if os.path.isdir(d)})
    os.makedirs(args.out, exist_ok=True)
    order = {"doctor": 0, "patient": 1, "mixed": 2}
    comp, ins = [], []
    for d in dirs:
        run = os.path.basename(os.path.normpath(d))
        extractor = (read(os.path.join(d, "wer.csv")) or [{}])[0].get("term_extractor", "")
        run_ins = read(os.path.join(d, "insertions.csv"))
        corrected = ({r["condition"]: r for r in read(os.path.join(args.corrected_root, run, "summary.csv"))}
                     if args.corrected_root else {})
        for s in read(os.path.join(d, "summary.csv")):
            long_runs = [int(r["n_words"]) for r in run_ins
                         if r["condition"] == s["condition"] and int(r["n_words"]) >= args.long_run]
            n = int(s["ref_words"])
            comp.append({
                "run": run, "condition": s["condition"], "model": s["model"],
                "n_consultations": s["n_consultations"], "audio_min": s["audio_min"], "ref_words": n,
                "wer": s["corpus_wer"],
                "wer_corrected": corrected.get(s["condition"], {}).get("corpus_wer", ""),
                "sub_rate": round(int(s["substitutions"]) / n, 4),
                "del_rate": round(int(s["deletions"]) / n, 4),
                "ins_rate": round(int(s["insertions"]) / n, 4),
                "term_recall": s["term_recall_pooled"], "term_extractor": extractor,
                "sec_per_audio_min": s["sec_per_audio_min"],
                "long_runs": len(long_runs), "long_run_words": sum(long_runs),
                **{k: s.get(k, "") for k in ("ov_overlap_s", "del_rate_in", "del_rate_out",
                                              "ins_rate_in", "ins_rate_out", "sub_rate_in", "sub_rate_out")},
            })
        ins += [{"run": run, **r} for r in run_ins]
    comp.sort(key=lambda r: (order.get(r["condition"], 9), r["run"]))
    top = sorted(ins, key=lambda r: -int(r["n_words"]))[:args.top]

    for name, data in (("comparison.csv", comp), ("top_insertions.csv", top)):
        if data:
            with open(os.path.join(args.out, name), "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
                w.writeheader()
                w.writerows(data)

    print(markdown(comp, [
        ("run", lambda r: r["run"]), ("condition", lambda r: r["condition"]),
        ("WER", lambda r: pct(r["wer"])), ("WER corrected", lambda r: pct(r["wer_corrected"])),
        ("sub", lambda r: pct(r["sub_rate"])),
        ("del", lambda r: pct(r["del_rate"])), ("ins", lambda r: pct(r["ins_rate"])),
        ("term recall", lambda r: pct(r["term_recall"])), ("terms", lambda r: r["term_extractor"].split("(")[0]),
        ("del in/out overlap", lambda r: f"{pct(r['del_rate_in'])} / {pct(r['del_rate_out'])}"),
        ("ins in/out overlap", lambda r: f"{pct(r['ins_rate_in'])} / {pct(r['ins_rate_out'])}"),
        (f"runs >= {args.long_run} words", lambda r: f"{r['long_runs']} ({r['long_run_words']} words)"),
        ("s/audio-min", lambda r: r["sec_per_audio_min"]),
    ]))
    print()
    print(markdown(top, [
        ("run", lambda r: r["run"]), ("id", lambda r: r["id"]), ("condition", lambda r: r["condition"]),
        ("t (s)", lambda r: r["segment_start_s"]), ("words", lambda r: r["n_words"]),
        ("inserted", lambda r: r["inserted"][:120]), ("reference there", lambda r: r["ref_context"]),
    ]))


if __name__ == "__main__":
    main()
