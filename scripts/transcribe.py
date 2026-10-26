"""Transcribe prepared PriMock57 audio with faster-whisper (default) or NVIDIA Parakeet.

Reads <data>/<cid>/{doctor,patient,mixed}.wav (from prep_data.py) and writes
<out>/<cid>/<condition>.json:
  {"id", "condition", "backend", "model", "initial_prompt", "audio_s",
   "runtime_s", "rtf", "text", "segments": [{"start", "end", "text", ...}]}
Existing outputs are skipped, so an interrupted run (e.g. a Colab disconnect)
can be resumed by re-running the same command.

Examples:
  # CPU smoke test
  python -I scripts/transcribe.py --data data/prepared_3min --out outputs/fw-base --model base
  # GPU (Colab)
  python -I scripts/transcribe.py --data data/prepared --out outputs/fw-large-v3 --model large-v3
  # with a domain prompt
  python -I scripts/transcribe.py ... --initial-prompt "A GP consultation between a doctor and a patient."
  # Parakeet (needs nemo_toolkit[asr]; untested in the smoke test)
  python -I scripts/transcribe.py --backend parakeet --data data/prepared --out outputs/parakeet
"""
import argparse
import json
import os
import time

import soundfile as sf


def load_faster_whisper(args):
    from faster_whisper import WhisperModel

    device = args.device
    if device == "auto":
        try:
            import ctranslate2
            device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
        except Exception:
            device = "cpu"
    compute_type = args.compute_type or ("float16" if device == "cuda" else "int8")
    print(f"faster-whisper {args.model} on {device} ({compute_type})")
    model = WhisperModel(args.model, device=device, compute_type=compute_type,
                         cpu_threads=args.cpu_threads)

    def run(wav_path):
        segments, info = model.transcribe(
            wav_path,
            language="en",
            beam_size=args.beam_size,
            initial_prompt=args.initial_prompt,
            vad_filter=args.vad,
            condition_on_previous_text=not args.no_condition_on_previous_text,
            word_timestamps=args.word_timestamps,
            hallucination_silence_threshold=args.hallucination_silence_threshold,
        )
        out = []
        for s in segments:  # generator: decoding happens here
            seg = {
                "start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip(),
                "avg_logprob": round(s.avg_logprob, 3),
                "no_speech_prob": round(s.no_speech_prob, 3),
                "compression_ratio": round(s.compression_ratio, 3),
            }
            if s.words:
                seg["words"] = [{"start": round(w.start, 2), "end": round(w.end, 2), "word": w.word,
                                 "probability": round(w.probability, 3)} for w in s.words]
            out.append(seg)
        return out

    return run


def load_parakeet(args):
    import nemo.collections.asr as nemo_asr

    name = args.model if args.model.startswith("nvidia/") else "nvidia/parakeet-tdt-0.6b-v2"
    args.model = name  # recorded in the output JSON
    print(f"NeMo {name}")
    model = nemo_asr.models.ASRModel.from_pretrained(model_name=name)
    if args.local_attention:
        # full attention handles ~24 min on an A100; local attention allows longer audio
        model.change_attention_model("rel_pos_local_attn", [256, 256])
        model.change_subsampling_conv_chunking_factor(1)

    def run(wav_path):
        hyp = model.transcribe([wav_path], timestamps=True)[0]
        segs = hyp.timestamp.get("segment", []) if getattr(hyp, "timestamp", None) else []
        if not segs:
            return [{"start": 0.0, "end": None, "text": hyp.text.strip()}]
        return [{"start": round(s["start"], 2), "end": round(s["end"], 2), "text": s["segment"].strip()}
                for s in segs]

    return run


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/prepared")
    ap.add_argument("--out", required=True)
    ap.add_argument("--backend", choices=["faster-whisper", "parakeet"], default="faster-whisper")
    ap.add_argument("--model", default="base",
                    help="faster-whisper: tiny/base/small/medium/large-v3/large-v3-turbo; "
                         "parakeet: nvidia/parakeet-tdt-0.6b-v2")
    ap.add_argument("--conditions", nargs="+", default=["doctor", "patient", "mixed"])
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--initial-prompt", default=None)
    ap.add_argument("--beam-size", type=int, default=5)
    ap.add_argument("--vad", action="store_true", help="faster-whisper Silero VAD filter (off by default)")
    ap.add_argument("--no-condition-on-previous-text", action="store_true")
    ap.add_argument("--word-timestamps", action="store_true", help="faster-whisper: store per-word times")
    ap.add_argument("--hallucination-silence-threshold", type=float, default=None,
                    help="faster-whisper: skip silent periods longer than this (s) around suspected "
                         "hallucinations; turns on --word-timestamps")
    ap.add_argument("--device", default="auto")
    ap.add_argument("--compute-type", default=None)
    ap.add_argument("--cpu-threads", type=int, default=0)
    ap.add_argument("--local-attention", action="store_true", help="parakeet: for audio > ~20 min")
    args = ap.parse_args()
    if args.hallucination_silence_threshold is not None:
        args.word_timestamps = True  # faster-whisper ignores the threshold without word timestamps

    ids = sorted(d for d in os.listdir(args.data) if os.path.isdir(os.path.join(args.data, d)))
    if args.ids:
        ids = [i for i in ids if i in set(args.ids)]
    if args.limit:
        ids = ids[: args.limit]

    run = load_parakeet(args) if args.backend == "parakeet" else load_faster_whisper(args)

    for cid in ids:
        os.makedirs(os.path.join(args.out, cid), exist_ok=True)
        for cond in args.conditions:
            out_path = os.path.join(args.out, cid, f"{cond}.json")
            if os.path.exists(out_path):
                print(f"skip {out_path}")
                continue
            wav = os.path.join(args.data, cid, f"{cond}.wav")
            audio_s = sf.info(wav).duration
            t0 = time.time()
            segments = run(wav)
            runtime = time.time() - t0
            result = {
                "id": cid, "condition": cond, "backend": args.backend, "model": args.model,
                "initial_prompt": args.initial_prompt,
                "settings": {"vad": args.vad, "beam_size": args.beam_size,
                             "condition_on_previous_text": not args.no_condition_on_previous_text,
                             "word_timestamps": args.word_timestamps,
                             "hallucination_silence_threshold": args.hallucination_silence_threshold}
                if args.backend == "faster-whisper" else {"local_attention": args.local_attention},
                "audio_s": round(audio_s, 2),
                "runtime_s": round(runtime, 2), "rtf": round(runtime / audio_s, 4),
                "text": " ".join(s["text"] for s in segments),
                "segments": segments,
            }
            with open(out_path, "w") as f:
                json.dump(result, f, indent=1)
            print(f"{cid}/{cond}: {audio_s:.0f}s audio in {runtime:.1f}s "
                  f"({runtime / (audio_s / 60):.1f}s per audio-minute)")


if __name__ == "__main__":
    main()
