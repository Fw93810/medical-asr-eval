"""Cut long audio into chunks for ASR models that only take short inputs.

Models such as Granite Speech and Cohere Transcribe have no long-form decoding of
their own (or split at fixed lengths), and a cut in the middle of a word makes a
stitching error. This plans the cuts once, from speech activity, and every such
model then uses the same plan:

  1. Silero VAD (the one bundled with faster-whisper) finds speech regions.
  2. Consecutive regions are merged while the chunk stays <= --max-s seconds;
     a chunk always ends in a pause, never inside speech.
  3. A single region longer than --max-s is split at the quietest 100 ms frame in
     the second half of each window.
  4. Each chunk is padded by --pad-s on both sides (never past the neighbouring
     chunk), so word onsets and endings are not clipped.

Audio outside every chunk (long silences) is not transcribed, as with the VAD
filter used for Whisper. Writes <out>/<cid>/<condition>.json: [[start_s, end_s], ...].

Usage:
  python -I scripts/plan_chunks.py --data data/prepared_test47 --out outputs/chunks/test47
"""
import argparse
import json
import os

import numpy as np
import soundfile as sf
from faster_whisper.vad import VadOptions, get_speech_timestamps

SR = 16000


def split_long(audio, start, end, max_s):
    """Split [start, end) (samples) at quiet frames so no piece exceeds max_s."""
    pieces, frame = [], SR // 10
    while (end - start) / SR > max_s:
        lo, hi = start + int(max_s * SR / 2), start + int(max_s * SR)
        frames = [(np.sqrt(np.mean(audio[i:i + frame] ** 2)), i) for i in range(lo, hi - frame, frame // 2)]
        cut = min(frames)[1] + frame // 2
        pieces.append((start, cut))
        start = cut
    pieces.append((start, end))
    return pieces


def plan(audio, max_s, pad_s, min_silence_ms):
    speech = get_speech_timestamps(audio, VadOptions(min_silence_duration_ms=min_silence_ms, speech_pad_ms=0))
    regions = []
    for s in speech:
        regions += split_long(audio, s["start"], s["end"], max_s)
    chunks = []
    for a, b in regions:
        if chunks and (b - chunks[-1][0]) / SR <= max_s:
            chunks[-1][1] = b
        else:
            chunks.append([a, b])
    pad = int(pad_s * SR)
    out = []
    for k, (a, b) in enumerate(chunks):
        lo = max(0, a - pad, (chunks[k - 1][1] + a) // 2 if k else 0)
        hi = min(len(audio), b + pad, (b + chunks[k + 1][0]) // 2 if k + 1 < len(chunks) else len(audio))
        out.append([round(lo / SR, 3), round(hi / SR, 3)])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--conditions", nargs="+", default=["doctor", "patient", "mixed"])
    ap.add_argument("--max-s", type=float, default=30.0)
    ap.add_argument("--pad-s", type=float, default=0.3)
    ap.add_argument("--min-silence-ms", type=int, default=300)
    args = ap.parse_args()

    stats = []
    for cid in sorted(os.listdir(args.data)):
        for cond in args.conditions:
            wav = os.path.join(args.data, cid, f"{cond}.wav")
            if not os.path.isfile(wav):
                continue
            audio, sr = sf.read(wav, dtype="float32")
            assert sr == SR, f"{wav}: expected 16 kHz"
            chunks = plan(audio, args.max_s, args.pad_s, args.min_silence_ms)
            os.makedirs(os.path.join(args.out, cid), exist_ok=True)
            with open(os.path.join(args.out, cid, f"{cond}.json"), "w") as f:
                json.dump({"max_s": args.max_s, "pad_s": args.pad_s, "min_silence_ms": args.min_silence_ms,
                           "audio_s": round(len(audio) / SR, 2), "chunks": chunks}, f)
            lens = [b - a for a, b in chunks]
            stats.append((len(chunks), sum(lens), max(lens), len(audio) / SR))
    n = sum(s[0] for s in stats)
    print(f"{len(stats)} files, {n} chunks, longest {max(s[2] for s in stats):.1f}s, "
          f"{sum(s[1] for s in stats) / sum(s[3] for s in stats):.1%} of the audio kept")


if __name__ == "__main__":
    main()
