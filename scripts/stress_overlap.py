"""Stress test S1: more doctor-patient overlap, by re-timing utterances.

Every utterance is cut from its own speaker's clean channel (with a short pad,
never reaching into the same speaker's neighbouring utterance) and placed on a new
time line. At a share p of the turn changes (an utterance whose speaker differs
from the previous one), the new speaker starts d seconds earlier, into the previous
speaker's utterance; everything after it moves earlier by the same amount, so the
rest of the conversation keeps its own timing. Limits:
  * the new speaker never starts before the previous utterance has run min_lead_s;
  * a speaker's utterances never overlap each other.
Level 1x uses d = 0: the same cut-and-place synthesis with the original timing, so
every level shares the synthesis artefacts and only the overlap changes.

Writes, per level, a prepared folder in the same format as prep_data.py
(mixed.wav summed and peak-normalised to -1 dBFS, utterances.json with the new times,
ref_*.txt), so transcribe.py and evaluate.py run on it unchanged. The separated
channels are not written: S1 only transcribes the mixed channel.

Overlap ratio = seconds where both speakers talk / seconds where anyone talks
(utterance intervals). --calibrate prints it for a range of d, to pick the d that
reaches 2x and 3x the baseline ratio on the dev set.

Usage:
  python -I scripts/stress_overlap.py --config configs/stress/s1_overlap.yaml --data data/prepared_full10 \
      --out data/stress/full10 --calibrate 0 0.5 1 1.5 2
  python -I scripts/stress_overlap.py --config configs/stress/s1_overlap.yaml --data data/prepared_full10 \
      --out data/stress/full10
"""
import argparse
import json
import os
import random

import numpy as np
import soundfile as sf
import yaml

SR = 16000


def union_length(intervals):
    total, end = 0.0, -1e9
    for a, b in sorted(intervals):
        if b > end:
            total += b - max(a, end)
            end = b
    return total


def overlap_ratio(utts):
    doc = [(u["start"], u["end"]) for u in utts if u["speaker"] == "doctor"]
    pat = [(u["start"], u["end"]) for u in utts if u["speaker"] == "patient"]
    both = [(max(a, c), min(b, d)) for a, b in doc for c, d in pat if max(a, c) < min(b, d)]
    speech = union_length(doc + pat)
    return union_length(both) / speech if speech else 0.0, union_length(both), speech


def retime(utts, p, d, min_lead_s, gap_s, rng):
    """New (start, end) per utterance; utts sorted by start. Returns list and number of shifted turns."""
    new, shift, shifted = [], 0.0, 0
    last_end = {}  # speaker -> new end of their latest utterance
    for i, u in enumerate(utts):
        s, e = u["start"] - shift, u["end"] - shift
        if i and u["speaker"] != utts[i - 1]["speaker"] and d > 0 and rng.random() < p:
            prev_s = new[i - 1][0]
            extra = min(d, s - (prev_s + min_lead_s))
            if u["speaker"] in last_end:
                extra = min(extra, s - (last_end[u["speaker"]] + gap_s))
            if extra > 0:
                shift += extra
                s, e = s - extra, e - extra
                shifted += 1
        if u["speaker"] in last_end and s < last_end[u["speaker"]] + gap_s:  # keep a speaker's own order
            push = last_end[u["speaker"]] + gap_s - s
            shift -= push
            s, e = s + push, e + push
        new.append((s, e))
        last_end[u["speaker"]] = max(last_end.get(u["speaker"], -1e9), e)
    return new, shifted


def synth(cid, data, utts, new, pad_s):
    """Mixed audio for the new timing; each utterance's audio comes from its own channel."""
    chans = {spk: sf.read(os.path.join(data, cid, f"{spk}.wav"), dtype="float32")[0] for spk in ("doctor", "patient")}
    length = int((max(e for _, e in new) + 1.0) * SR)
    mixed = np.zeros(length, dtype=np.float32)
    for k, (u, (s, _)) in enumerate(zip(utts, new)):
        same = [v for v in utts if v["speaker"] == u["speaker"] and v is not u]
        before = max((v["end"] for v in same if v["end"] <= u["start"]), default=0.0)
        after = min((v["start"] for v in same if v["start"] >= u["end"]), default=1e9)
        a = max(u["start"] - pad_s, (before + u["start"]) / 2, 0.0)
        b = min(u["end"] + pad_s, (u["end"] + after) / 2)
        clip = chans[u["speaker"]][int(a * SR):int(b * SR)]
        at = int((s - (u["start"] - a)) * SR)
        if at < 0:
            clip, at = clip[-at:], 0
        clip = clip[:length - at]
        mixed[at:at + len(clip)] += clip
    peak = float(np.max(np.abs(mixed))) or 1.0
    return mixed * (10 ** (-1 / 20) / peak)


def write_prepared(out_dir, cid, meta, utts, new, mixed):
    d = os.path.join(out_dir, cid)
    os.makedirs(d, exist_ok=True)
    moved = [{**u, "start": round(s, 3), "end": round(e, 3), "orig_start": u["start"]} for u, (s, e) in zip(utts, new)]
    moved.sort(key=lambda u: u["start"])
    sf.write(os.path.join(d, "mixed.wav"), mixed, SR, subtype="PCM_16")
    with open(os.path.join(d, "utterances.json"), "w") as f:
        json.dump({**meta, "duration_s": len(mixed) / SR, "utterances": moved}, f)
    for spk in ("doctor", "patient"):
        with open(os.path.join(d, f"ref_{spk}.txt"), "w") as f:
            f.write("\n".join(u["text"] for u in moved if u["speaker"] == spk) + "\n")
    with open(os.path.join(d, "ref_mixed.txt"), "w") as f:
        f.write("\n".join(u["text"] for u in moved) + "\n")
    with open(os.path.join(d, "ref_mixed_speakers.txt"), "w") as f:
        for u in moved:
            f.write(f"[{u['start']:7.2f}-{u['end']:7.2f}] {u['speaker'].capitalize()}: {u['text']}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True, help="parent folder; one subfolder per level")
    ap.add_argument("--calibrate", nargs="*", type=float, help="only print the overlap ratio for these d values")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config))

    cids = sorted(c for c in os.listdir(args.data) if os.path.isfile(os.path.join(args.data, c, "utterances.json")))
    loaded = {}
    for cid in cids:
        meta = json.load(open(os.path.join(args.data, cid, "utterances.json")))
        loaded[cid] = (meta, sorted(meta["utterances"], key=lambda u: u["start"]))

    def run(d):
        tot_ov = tot_sp = shifted = turns = 0
        res = {}
        for k, cid in enumerate(cids):
            meta, utts = loaded[cid]
            rng = random.Random(f"{cfg['seed']}:{cid}")  # same draws for every d
            new, n = retime(utts, cfg["p"], d, cfg["min_lead_s"], cfg["gap_s"], rng)
            _, ov, sp = overlap_ratio([{**u, "start": s, "end": e} for u, (s, e) in zip(utts, new)])
            tot_ov, tot_sp, shifted = tot_ov + ov, tot_sp + sp, shifted + n
            turns += sum(utts[i]["speaker"] != utts[i - 1]["speaker"] for i in range(1, len(utts)))
            res[cid] = new
        return res, tot_ov / tot_sp, shifted, turns

    _, base, _, _ = run(0.0)
    if args.calibrate is not None:
        for d in args.calibrate:
            _, r, n, turns = run(d)
            print(f"d={d:.2f}s: overlap ratio {r:.4f} = {r / base:.2f}x baseline; shifted {n}/{turns} turn changes")
        return

    report = []
    for level, d in cfg["levels"].items():
        res, r, n, turns = run(float(d))
        for cid in cids:
            meta, utts = loaded[cid]
            mixed = synth(cid, args.data, utts, res[cid], cfg["pad_s"])
            meta_out = {k: v for k, v in meta.items() if k != "utterances"}
            meta_out["stress"] = {"factor": "S1 overlap", "level": level, "d_s": d, **{k: cfg[k] for k in
                                  ("seed", "p", "min_lead_s", "gap_s", "pad_s")}}
            write_prepared(os.path.join(args.out, level), cid, meta_out, utts, res[cid], mixed)
        report.append({"level": level, "d_s": d, "overlap_ratio": round(r, 4), "x_baseline": round(r / base, 2),
                       "shifted_turns": n, "turn_changes": turns})
        print(report[-1])
    with open(os.path.join(args.out, "s1_levels.json"), "w") as f:
        json.dump({"baseline_ratio": round(base, 4), "levels": report}, f, indent=1)


if __name__ == "__main__":
    main()
