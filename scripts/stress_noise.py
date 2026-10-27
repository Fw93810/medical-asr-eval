"""Stress test S3: background noise at fixed signal-to-noise ratios.

Adds DEMAND environment noise to the original mixed channel (prep_data.py output);
the reference is unchanged, so the no-noise baseline is the existing stage-2 run.
Per consultation, a seeded draw picks one environment from the config; its 16
channels (one microphone array, about 5 min each) are joined in a seeded order and
a seeded offset is cut from them, so a 10-minute consultation never hears the same
noise twice. SNR = speech power / noise power, with speech power measured only
inside utterance intervals (either speaker). After mixing, the result is
peak-normalised to -1 dBFS like the baseline.

A level can also add alarms (S3b): on top of the same background noise, alarm
events (excerpts of 3-6 s from the alarm files, 20 ms fades) are placed at random:
each minute gets a seeded number of events within alarms.per_minute. Each event is
scaled so its power is alarms.db_rel_speech relative to the speech power. The
background noise is the same draw as for the plain levels, so an alarm level differs
from the plain level with the same SNR only by the alarms.

Writes one prepared folder per level (mixed.wav, utterances.json, ref_*.txt) and
<out>/s3_levels.json with the achieved SNR, the environment and the alarm events
per consultation.

Usage:
  python -I scripts/stress_noise.py --config configs/stress/s3_noise.yaml --data data/prepared_full10 \
      --out data/stress/full10
"""
import argparse
import glob
import json
import os
import random
import shutil

import numpy as np
import soundfile as sf
import yaml
from scipy.signal import resample_poly

SR = 16000


def load_mono_16k(path):
    audio, sr = sf.read(path, dtype="float32", always_2d=True)
    audio = audio.mean(axis=1)
    return audio if sr == SR else resample_poly(audio, SR, sr).astype(np.float32)


def alarm_track(n, files, cfg, p_speech, rng):
    """Alarm events over n samples; returns (track, [(start_s, end_s, file)])."""
    track, events = np.zeros(n, dtype=np.float32), []
    fade = int(0.02 * SR)
    lo, hi = cfg["per_minute"]
    for m in range(int(np.ceil(n / (60 * SR)))):
        for _ in range(rng.randint(lo, hi)):
            name = rng.choice(sorted(files))
            src = files[name]
            dur = min(int(rng.uniform(*cfg["event_s"]) * SR), len(src))
            a = rng.randrange(len(src) - dur + 1)
            clip = src[a:a + dur].copy()
            ramp = np.linspace(0, 1, fade, dtype=np.float32)
            clip[:fade] *= ramp
            clip[-fade:] *= ramp[::-1]
            clip *= np.sqrt(p_speech * 10 ** (cfg["db_rel_speech"] / 10) / float(np.mean(clip ** 2)))
            at = int((m * 60 + rng.uniform(0, 60)) * SR)
            if at >= n:
                continue
            clip = clip[:n - at]
            track[at:at + len(clip)] += clip
            events.append((round(at / SR, 2), round((at + len(clip)) / SR, 2), name))
    return track, sorted(events)


def speech_mask(utts, n):
    mask = np.zeros(n, dtype=bool)
    for u in utts:
        mask[int(u["start"] * SR):int(u["end"] * SR)] = True
    return mask


def noise_track(env_dir, n, rng):
    chans = sorted(glob.glob(os.path.join(env_dir, "ch*.wav")))
    rng.shuffle(chans)
    joined = np.concatenate([sf.read(c, dtype="float32")[0] for c in chans])
    assert len(joined) > n, f"{env_dir}: noise shorter than the audio"
    at = rng.randrange(len(joined) - n)
    return joined[at:at + n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True, help="parent folder; one subfolder per level")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config))

    cids = sorted(c for c in os.listdir(args.data) if os.path.isfile(os.path.join(args.data, c, "utterances.json")))
    report = {"config": cfg, "consultations": {}}
    alarms = {os.path.basename(f): load_mono_16k(f) for f in cfg["alarms"]["files"]} if "alarms" in cfg else {}
    for cid in cids:
        src = os.path.join(args.data, cid)
        speech, sr = sf.read(os.path.join(src, "mixed.wav"), dtype="float32")
        assert sr == SR
        meta = json.load(open(os.path.join(src, "utterances.json")))
        mask = speech_mask(meta["utterances"], len(speech))
        p_speech = float(np.mean(speech[mask] ** 2))
        rng = random.Random(f"{cfg['seed']}:{cid}")
        env = rng.choice(cfg["environments"])
        noise = noise_track(os.path.join(cfg["noise_root"], env), len(speech), rng)
        p_noise = float(np.mean(noise ** 2))
        report["consultations"][cid] = {"environment": env, "snr_db": {}}
        if alarms:  # drawn after the noise, so adding alarms leaves the noise draw unchanged
            alarm, events = alarm_track(len(speech), alarms, cfg["alarms"], p_speech, rng)
            report["consultations"][cid]["alarm_events"] = events
        for level, spec in cfg["levels"].items():
            snr, with_alarms = (spec, False) if not isinstance(spec, dict) else (spec["snr"], spec.get("alarms", False))
            gain = np.sqrt(p_speech / (p_noise * 10 ** (snr / 10)))
            mixed = speech + gain * noise + (alarm if with_alarms else 0)
            achieved = 10 * np.log10(p_speech / float(np.mean((gain * noise)[mask] ** 2)))
            mixed = mixed * (10 ** (-1 / 20) / float(np.max(np.abs(mixed))))
            d = os.path.join(args.out, level, cid)
            os.makedirs(d, exist_ok=True)
            sf.write(os.path.join(d, "mixed.wav"), mixed, SR, subtype="PCM_16")
            with open(os.path.join(d, "utterances.json"), "w") as f:
                json.dump({**meta, "stress": {"factor": "S3b noise + alarms" if with_alarms else "S3 noise",
                                              "level": level, "snr_db": snr, "environment": env,
                                              "seed": cfg["seed"]}}, f)
            for name in ("ref_doctor.txt", "ref_patient.txt", "ref_mixed.txt", "ref_mixed_speakers.txt"):
                shutil.copy(os.path.join(src, name), d)
            report["consultations"][cid]["snr_db"][level] = round(achieved, 2)
        print(cid, env, report["consultations"][cid]["snr_db"])
    with open(os.path.join(args.out, "s3_levels.json"), "w") as f:
        json.dump(report, f, indent=1)


if __name__ == "__main__":
    main()
