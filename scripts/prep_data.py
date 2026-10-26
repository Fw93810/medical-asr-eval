"""Prepare PriMock57 consultations for ASR evaluation.

For each consultation <cid> it writes to <out>/<cid>/:
  doctor.wav, patient.wav   16 kHz mono (copied, optionally cropped)
  mixed.wav                 doctor + patient summed, peak-normalised to -1 dBFS
                            (simulates one room microphone)
  ref_doctor.txt            reference text for the doctor channel
  ref_patient.txt           reference text for the patient channel
  ref_mixed.txt             both channels' utterances merged in start-time order
  ref_mixed_speakers.txt    same, one utterance per line with "Doctor:/Patient:" and times
  utterances.json           all utterances: speaker, start, end, raw text, clean text

Reference cleaning: <UNSURE>...</UNSURE> tags are removed but their words kept;
<UNIN/> and <INAUDIBLE_SPEECH/> markers are dropped. Further normalisation
(case, punctuation, numbers) happens in evaluate.py.

--max-seconds N crops each consultation for quick tests. The crop point is the
latest time <= N that falls in a gap of BOTH channels, so no utterance is cut
in half; only utterances ending before the crop point are kept.

Usage:
  python -I scripts/prep_data.py --src data/primock57 --out data/prepared
  python -I scripts/prep_data.py --src data/primock57 --out data/prepared_3min --max-seconds 180 --limit 3
"""
import argparse
import json
import os
import re

import numpy as np
import soundfile as sf

SR = 16000
DROP_TAGS = ["<UNSURE>", "</UNSURE>", "<UNIN/>", "<INAUDIBLE_SPEECH/>"]


def read_textgrid(path):
    """Minimal parser for Praat long-format TextGrid files (single IntervalTier).

    Returns a list of (xmin, xmax, text) for non-empty intervals."""
    with open(path, encoding="utf-8") as f:
        content = f.read()
    pattern = re.compile(
        r'intervals \[\d+\]:\s*xmin = ([\d.eE+-]+)\s*xmax = ([\d.eE+-]+)\s*text = "((?:[^"]|"")*)"',
        re.S,
    )
    out = []
    for xmin, xmax, text in pattern.findall(content):
        text = text.replace('""', '"').strip()
        if text:
            out.append((float(xmin), float(xmax), text))
    return out


def clean(text):
    for tag in DROP_TAGS:
        text = text.replace(tag, " ")
    return re.sub(r"\s+", " ", text).strip()


def find_crop_point(utts, max_s):
    """Latest utterance end <= max_s that is not inside any utterance (either speaker)."""
    for t in sorted({u["end"] for u in utts if u["end"] <= max_s}, reverse=True):
        if not any(u["start"] < t < u["end"] for u in utts):
            return t
    return max_s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="data/primock57")
    ap.add_argument("--out", default="data/prepared")
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--max-seconds", type=float, help="crop each consultation (quick tests)")
    args = ap.parse_args()

    tdir = os.path.join(args.src, "transcripts")
    ids = sorted(f[: -len("_doctor.TextGrid")] for f in os.listdir(tdir) if f.endswith("_doctor.TextGrid"))
    if args.ids:
        ids = [i for i in ids if i in set(args.ids)]
    if args.limit:
        ids = ids[: args.limit]

    for cid in ids:
        wavs, utts = {}, []
        for spk in ("doctor", "patient"):
            wav_path = os.path.join(args.src, "audio", f"{cid}_{spk}.wav")
            if os.path.getsize(wav_path) < 1024:
                raise SystemExit(f"{wav_path} is a Git LFS pointer; run download_data.py first")
            audio, sr = sf.read(wav_path, dtype="float32")
            assert sr == SR and audio.ndim == 1, (wav_path, sr, audio.shape)
            wavs[spk] = audio
            for s, e, t in read_textgrid(os.path.join(tdir, f"{cid}_{spk}.TextGrid")):
                c = clean(t)
                if c:
                    utts.append({"speaker": spk, "start": s, "end": e, "raw": t, "text": c})
        utts.sort(key=lambda u: u["start"])

        # channels can differ by a few samples -> pad to the same length
        n = max(len(a) for a in wavs.values())
        for spk in wavs:
            wavs[spk] = np.pad(wavs[spk], (0, n - len(wavs[spk])))

        crop_s = None
        if args.max_seconds and n / SR > args.max_seconds:
            crop_s = find_crop_point(utts, args.max_seconds)
            utts = [u for u in utts if u["end"] <= crop_s]
            for spk in wavs:
                wavs[spk] = wavs[spk][: int(crop_s * SR)]

        mixed = wavs["doctor"] + wavs["patient"]
        peak = float(np.max(np.abs(mixed))) or 1.0
        mixed = mixed * (10 ** (-1 / 20) / peak)

        d = os.path.join(args.out, cid)
        os.makedirs(d, exist_ok=True)
        for name, audio in [("doctor", wavs["doctor"]), ("patient", wavs["patient"]), ("mixed", mixed)]:
            sf.write(os.path.join(d, f"{name}.wav"), audio, SR, subtype="PCM_16")
        for spk in ("doctor", "patient"):
            with open(os.path.join(d, f"ref_{spk}.txt"), "w") as f:
                f.write("\n".join(u["text"] for u in utts if u["speaker"] == spk) + "\n")
        with open(os.path.join(d, "ref_mixed.txt"), "w") as f:
            f.write("\n".join(u["text"] for u in utts) + "\n")
        with open(os.path.join(d, "ref_mixed_speakers.txt"), "w") as f:
            for u in utts:
                f.write(f"[{u['start']:7.2f}-{u['end']:7.2f}] {u['speaker'].capitalize()}: {u['text']}\n")
        meta = {"id": cid, "duration_s": len(mixed) / SR, "cropped_at_s": crop_s, "utterances": utts}
        with open(os.path.join(d, "utterances.json"), "w") as f:
            json.dump(meta, f, indent=1)
        n_words = sum(len(u["text"].split()) for u in utts)
        print(f"{cid}: {len(mixed) / SR:6.1f}s, {len(utts)} utterances, {n_words} ref words"
              + (f" (cropped at {crop_s:.1f}s)" if crop_s else ""))


if __name__ == "__main__":
    main()
