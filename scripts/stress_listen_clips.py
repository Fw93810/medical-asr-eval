"""Cut listening clips from synthesised stress conditions, for a human check.

For each of --n consultations (drawn with --seed), picks the 30 s window with the
most overlap in the highest level, finds the same stretch of conversation (same
first utterance) in every level, and writes <out>/<cid>_<level>.wav plus
clips.csv with each clip's source times and overlap seconds.

Usage:
  python -I scripts/stress_listen_clips.py --root data/stress/full10 --levels s1_1x s1_2x s1_3x \
      --out results/stress/listen
"""
import argparse
import csv
import json
import os
import random

import soundfile as sf

SR = 16000


def overlap_in(utts, a, b):
    doc = [(u["start"], u["end"]) for u in utts if u["speaker"] == "doctor"]
    pat = [(u["start"], u["end"]) for u in utts if u["speaker"] == "patient"]
    tot = 0.0
    for s, e in doc:
        for c, d in pat:
            lo, hi = max(s, c, a), min(e, d, b)
            tot += max(0.0, hi - lo)
    return tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--levels", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--seconds", type=float, default=30.0)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    top = os.path.join(args.root, args.levels[-1])
    cids = sorted(os.listdir(top))
    picked = sorted(random.Random(args.seed).sample(cids, args.n))
    rows = []
    for cid in picked:
        utts = {lv: json.load(open(os.path.join(args.root, lv, cid, "utterances.json")))["utterances"]
                for lv in args.levels}
        # window in the top level starting at an utterance, with the most overlap
        hi = utts[args.levels[-1]]
        best = max(range(len(hi)), key=lambda k: overlap_in(hi, hi[k]["start"], hi[k]["start"] + args.seconds))
        key = (hi[best]["speaker"], hi[best]["orig_start"])
        for lv in args.levels:
            first = next(u for u in utts[lv] if (u["speaker"], u["orig_start"]) == key)
            a = max(0.0, first["start"] - 0.5)
            b = a + args.seconds
            audio, sr = sf.read(os.path.join(args.root, lv, cid, "mixed.wav"), dtype="float32")
            name = f"{cid}_{lv}.wav"
            sf.write(os.path.join(args.out, name), audio[int(a * SR):int(b * SR)], SR, subtype="PCM_16")
            rows.append({"file": name, "id": cid, "level": lv, "start_s": round(a, 2), "end_s": round(b, 2),
                         "overlap_s_in_clip": round(overlap_in(utts[lv], a, b), 2)})
            print(rows[-1])
    with open(os.path.join(args.out, "clips.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
