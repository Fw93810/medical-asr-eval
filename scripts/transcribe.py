"""Transcribe prepared PriMock57 audio with faster-whisper (default), NVIDIA Parakeet,
IBM Granite Speech, Cohere Transcribe, Qwen3-ASR or Canary-Qwen.

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
  # Parakeet (needs nemo_toolkit[asr])
  python -I scripts/transcribe.py --backend parakeet --data data/prepared --out outputs/parakeet
  # Granite Speech / Cohere Transcribe (transformers; short inputs, so they read a chunk plan
  # from plan_chunks.py and each chunk becomes one segment with the chunk's start and end)
  python -I scripts/transcribe.py --backend granite --chunks outputs/chunks/test47 --data data/prepared_test47 ...
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
            vad_parameters={"speech_pad_ms": args.vad_speech_pad_ms} if args.vad_speech_pad_ms else None,
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

    if args.chunks:  # same chunk plan as the short-input models; each chunk decoded on its own
        return chunked(args, lambda chunk: " ".join(s["text"] for s in run(chunk)))
    return run


def via_wav(transcribe_path):
    """Adapt a model that only takes file paths to chunked(): write each chunk to a temp wav."""
    import tempfile

    def one(chunk):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "chunk.wav")
            sf.write(path, chunk, 16000)
            return transcribe_path(path)

    return one


def chunked(args, transcribe_chunk=None, transcribe_batch=None):
    """run(wav) for models that take short inputs: the chunks of the plan, one at a time
    (transcribe_chunk) or --batch-size at a time (transcribe_batch: list of arrays -> list of texts).
    Batches are formed from chunks of similar length to keep padding small; results are put
    back in time order."""
    def run(wav_path):
        cid = os.path.basename(os.path.dirname(wav_path))
        cond = os.path.splitext(os.path.basename(wav_path))[0]
        with open(os.path.join(args.chunks, cid, f"{cond}.json")) as f:
            plan = json.load(f)["chunks"]
        audio, sr = sf.read(wav_path, dtype="float32")
        pieces = [audio[int(a * sr):int(b * sr)] for a, b in plan]
        texts = [None] * len(plan)
        if transcribe_batch and args.batch_size > 1:
            order = sorted(range(len(plan)), key=lambda k: len(pieces[k]))
            for s in range(0, len(order), args.batch_size):
                idx = order[s:s + args.batch_size]
                for k, t in zip(idx, transcribe_batch([pieces[k] for k in idx])):
                    texts[k] = t
        else:
            one = transcribe_chunk or (lambda p: transcribe_batch([p])[0])
            texts = [one(p) for p in pieces]
        return [{"start": a, "end": b, "text": t.strip()} for (a, b), t in zip(plan, texts) if t.strip()]

    return run


def load_granite(args):
    import torch
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

    name = args.model if "/" in args.model else "ibm-granite/granite-speech-4.1-2b"
    args.model = name
    print(f"transformers {name} (chunks: {args.chunks})")
    processor = AutoProcessor.from_pretrained(name)
    tokenizer = processor.tokenizer
    tokenizer.padding_side = "left"  # batched generation: prompts end where generation starts
    model = AutoModelForSpeechSeq2Seq.from_pretrained(name, device_map="cuda", torch_dtype=torch.bfloat16)
    chat = [{"role": "user", "content": "<|audio|>transcribe the speech with proper punctuation and capitalization."}]
    prompt = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)

    def batch(chunks):
        wavs = [torch.from_numpy(c) for c in chunks]
        inputs = processor([prompt] * len(chunks), wavs if len(wavs) > 1 else wavs[0].unsqueeze(0),
                           device="cuda", return_tensors="pt").to("cuda")
        with torch.inference_mode():
            out = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=False, num_beams=1)
        new = out[:, inputs["input_ids"].shape[-1]:]
        return tokenizer.batch_decode(new, add_special_tokens=False, skip_special_tokens=True)

    return chunked(args, transcribe_batch=batch)


def load_cohere(args):
    import torch
    from transformers import AutoProcessor, CohereAsrForConditionalGeneration

    name = args.model if "/" in args.model else "CohereLabs/cohere-transcribe-03-2026"
    args.model = name
    print(f"transformers {name} (chunks: {args.chunks})")
    processor = AutoProcessor.from_pretrained(name)
    model = CohereAsrForConditionalGeneration.from_pretrained(name, device_map="cuda", torch_dtype=torch.bfloat16)

    def batch(chunks):
        # chunks are <= ~31 s, under the processor's own 35 s clip length, so it does not split them;
        # audio_chunk_index is passed anyway so decode() would rejoin any split it made
        inputs = processor(chunks if len(chunks) > 1 else chunks[0], sampling_rate=16000, return_tensors="pt",
                           language="en")
        chunk_index = inputs.pop("audio_chunk_index", None)
        inputs = inputs.to(model.device, dtype=model.dtype)
        with torch.inference_mode():
            out = model.generate(**inputs, max_new_tokens=args.max_new_tokens)
        kw = {"audio_chunk_index": chunk_index, "language": "en"} if chunk_index is not None else {}
        text = processor.decode(out, skip_special_tokens=True, **kw)
        return text if isinstance(text, list) else [text]

    return chunked(args, transcribe_batch=batch)


def load_qwen3asr(args):
    import torch
    from qwen_asr import Qwen3ASRModel

    name = args.model if "/" in args.model else "Qwen/Qwen3-ASR-1.7B"
    args.model = name
    print(f"qwen-asr {name} (chunks: {args.chunks})")
    model = Qwen3ASRModel.from_pretrained(name, dtype=torch.bfloat16, device_map="cuda:0",
                                          max_inference_batch_size=args.batch_size, max_new_tokens=args.max_new_tokens)

    def batch(chunks):
        res = model.transcribe(audio=[(c, 16000) for c in chunks], language=["English"] * len(chunks))
        return [r.text for r in res]

    return chunked(args, transcribe_batch=batch)


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

    if args.chunks:
        return chunked(args, via_wav(lambda path: model.transcribe([path], verbose=False)[0].text))
    return run


def load_canary_qwen(args):
    from nemo.collections.speechlm2.models import SALM

    name = args.model if "/" in args.model else "nvidia/canary-qwen-2.5b"
    args.model = name
    print(f"NeMo SALM {name} (chunks: {args.chunks})")
    model = SALM.from_pretrained(name).bfloat16().eval().to("cuda")

    def one(path):
        prompt = [{"role": "user", "content": f"Transcribe the following: {model.audio_locator_tag}",
                   "audio": [path]}]
        ids = model.generate(prompts=[prompt], max_new_tokens=args.max_new_tokens)
        return model.tokenizer.ids_to_text(ids[0].cpu())

    return chunked(args, via_wav(one))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/prepared")
    ap.add_argument("--out", required=True)
    ap.add_argument("--backend", default="faster-whisper",
                    choices=["faster-whisper", "parakeet", "granite", "cohere", "qwen3asr", "canary-qwen"])
    ap.add_argument("--model", default="base",
                    help="faster-whisper: tiny/base/small/medium/large-v3/large-v3-turbo; "
                         "parakeet: nvidia/parakeet-tdt-0.6b-v2")
    ap.add_argument("--conditions", nargs="+", default=["doctor", "patient", "mixed"])
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--initial-prompt", default=None)
    ap.add_argument("--beam-size", type=int, default=5)
    ap.add_argument("--vad", action="store_true", help="faster-whisper Silero VAD filter (off by default)")
    ap.add_argument("--vad-speech-pad-ms", type=int, default=None,
                    help="padding kept around each detected speech region (faster-whisper default: 400)")
    ap.add_argument("--no-condition-on-previous-text", action="store_true")
    ap.add_argument("--word-timestamps", action="store_true", help="faster-whisper: store per-word times")
    ap.add_argument("--hallucination-silence-threshold", type=float, default=None,
                    help="faster-whisper: skip silent periods longer than this (s) around suspected "
                         "hallucinations; turns on --word-timestamps")
    ap.add_argument("--device", default="auto")
    ap.add_argument("--compute-type", default=None)
    ap.add_argument("--cpu-threads", type=int, default=0)
    ap.add_argument("--local-attention", action="store_true", help="parakeet: for audio > ~20 min")
    ap.add_argument("--chunks", help="chunk plan folder from plan_chunks.py: required for granite, cohere, "
                                     "qwen3asr, canary-qwen; optional for faster-whisper and parakeet")
    ap.add_argument("--max-new-tokens", type=int, default=400,
                    help="granite / cohere / qwen3asr / canary-qwen: per chunk")
    ap.add_argument("--batch-size", type=int, default=1,
                    help="granite / cohere / qwen3asr: chunks decoded together (1 = one at a time)")
    args = ap.parse_args()
    if args.hallucination_silence_threshold is not None:
        args.word_timestamps = True  # faster-whisper ignores the threshold without word timestamps

    ids = sorted(d for d in os.listdir(args.data) if os.path.isdir(os.path.join(args.data, d)))
    if args.ids:
        ids = [i for i in ids if i in set(args.ids)]
    if args.limit:
        ids = ids[: args.limit]

    loaders = {"faster-whisper": load_faster_whisper, "parakeet": load_parakeet, "granite": load_granite,
               "cohere": load_cohere, "qwen3asr": load_qwen3asr, "canary-qwen": load_canary_qwen}
    run = loaders[args.backend](args)

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
                "settings": {"vad": args.vad, "vad_speech_pad_ms": args.vad_speech_pad_ms, "beam_size": args.beam_size,
                             "condition_on_previous_text": not args.no_condition_on_previous_text,
                             "word_timestamps": args.word_timestamps,
                             "hallucination_silence_threshold": args.hallucination_silence_threshold,
                             "chunks": args.chunks}
                if args.backend == "faster-whisper" else
                {"local_attention": args.local_attention, "chunks": args.chunks} if args.backend == "parakeet" else
                {"chunks": args.chunks, "max_new_tokens": args.max_new_tokens, "batch_size": args.batch_size},
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
