"""Count long repetition loops in ASR output.

After the Whisper normaliser, finds
  * same-word runs: one word repeated consecutively >= --min-word times ("no no no ...");
  * phrase loops: a 2-4 word unit with at least two different words repeated
    consecutively >= --min-phrase times ("i know now that i know now that ...").
Loops are searched over the whole file (across segment boundaries); each loop
lists the segments it touches. The reference transcripts are searched the same
way, as a check that such runs are not real speech.

Writes <out>/repeats.csv (one row per loop) and <out>/summary.csv (per run and channel).

Usage:
  python -I scripts/count_repeats.py --data data/prepared_test47 --hyp outputs/test47-* --out results/test47/repeats
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # -I drops the script dir from sys.path
from evaluate import norm_words  # noqa: E402

CONDS = ("doctor", "patient", "mixed")


def loops(words, min_word, min_phrase, max_period=4):
    """[(start, end, period)] of repeated units, end exclusive; same-word runs first."""
    found, covered = [], [False] * len(words)
    for p in range(1, max_period + 1):
        need = min_word if p == 1 else min_phrase
        j = p
        while j < len(words):
            if words[j] != words[j - p]:
                j += 1
                continue
            s = j
            while j < len(words) and words[j] == words[j - p]:
                j += 1
            start, end = s - p, j
            reps = (end - start) // p
            unit = words[start:start + p]
            if reps >= need and (p == 1 or len(set(unit)) > 1) and sum(covered[start:end]) < (end - start) / 2:
                found.append((start, end, p))
                for k in range(start, end):
                    covered[k] = True
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--hyp", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-word", type=int, default=10)
    ap.add_argument("--min-phrase", type=int, default=5)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    cids = sorted(d for d in os.listdir(args.data) if os.path.isfile(os.path.join(args.data, d, "utterances.json")))
    rows, summary = [], []

    def scan(run, cid, cond, pieces):
        """pieces: [(start_s, end_s, text)] in time order."""
        words, seg_of = [], []
        for k, (_, _, text) in enumerate(pieces):
            ws = norm_words(text)
            words += ws
            seg_of += [k] * len(ws)
        out = []
        for a, b, p in loops(words, args.min_word, args.min_phrase):
            segs = sorted(set(seg_of[a:b]))
            out.append({"run": run, "id": cid, "condition": cond,
                        "kind": "same_word" if p == 1 else "phrase", "unit": " ".join(words[a:a + p]),
                        "repeats": (b - a) // p, "words": b - a,
                        "t_start": pieces[segs[0]][0], "t_end": pieces[segs[-1]][1], "segments": len(segs),
                        "text": " ".join(words[max(0, a - 5):a]) + " [" + " ".join(words[a:a + 3 * p]) + " ...]"})
        return out

    runs = []
    for cid in cids:
        with open(os.path.join(args.data, cid, "utterances.json")) as f:
            utts = sorted(json.load(f)["utterances"], key=lambda u: u["start"])
        for cond in CONDS:
            mine = [(u["start"], u["end"], u["text"]) for u in utts if cond == "mixed" or u["speaker"] == cond]
            rows += scan("reference", cid, cond, mine)
    runs.append("reference")
    for hyp_dir in args.hyp:
        run = os.path.basename(os.path.normpath(hyp_dir))
        runs.append(run)
        for cid in cids:
            for cond in CONDS:
                path = os.path.join(hyp_dir, cid, f"{cond}.json")
                if not os.path.isfile(path):
                    continue
                with open(path) as f:
                    segs = json.load(f)["segments"]
                rows += scan(run, cid, cond, [(s["start"], s["end"], s["text"]) for s in segs])

    agg = defaultdict(lambda: defaultdict(int))
    for r in rows:
        a = agg[(r["run"], r["condition"])]
        a[f"{r['kind']}_loops"] += 1
        a[f"{r['kind']}_words"] += r["words"]
        a[f"{r['kind']}_segments"] += r["segments"]
    for run in runs:
        for cond in CONDS:
            a = agg[(run, cond)]
            ids = {r["id"] for r in rows if r["run"] == run and r["condition"] == cond}
            summary.append({"run": run, "condition": cond,
                            **{f"{k}_{x}": a[f"{k}_{x}"] for k in ("same_word", "phrase") for x in ("loops", "words", "segments")},
                            "consultations_affected": len(ids)})

    for name, data in (("repeats.csv", rows), ("summary.csv", summary)):
        with open(os.path.join(args.out, name), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
            w.writeheader()
            w.writerows(data)
    print("| run | channel | same-word loops (words) | phrase loops (words) | consultations |")
    print("|---|---|---|---|---|")
    for s in summary:
        if s["same_word_loops"] or s["phrase_loops"]:
            print(f"| {s['run']} | {s['condition']} | {s['same_word_loops']} ({s['same_word_words']}) | "
                  f"{s['phrase_loops']} ({s['phrase_words']}) | {s['consultations_affected']} |")


if __name__ == "__main__":
    main()
