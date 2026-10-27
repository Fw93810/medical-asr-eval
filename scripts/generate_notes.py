"""Write a clinical note for each consultation from different transcripts, with a local LLM.

Sources (one note per consultation per source):
  human          the PriMock57 reference transcript, with Doctor:/Patient: labels
  asr_separated  ASR of the doctor and patient channels, interleaved by time and
                 labelled (perfect speaker separation); merged word by word into
                 speaker turns when the ASR has word timestamps, otherwise per segment
  asr_mixed      ASR of the mixed single channel, no speaker labels (one room
                 microphone, no diarisation)
Controls:
  human_unlabelled  the reference transcript without speaker labels
  <source>_plain    any source with the Whisper normaliser applied to each line
                    (lower case, no punctuation or fillers). human_unlabelled_plain
                    vs asr_mixed_plain differ only in the recognised words;
                    human vs human_plain shows how much the note changes from
                    surface form alone.

The model runs in Ollama on this machine (no data leaves it). Decoding is
greedy (temperature 0, fixed seed) and thinking is off, so reruns give the same
note. Outputs: <out>/<cid>/<source>.json. Existing outputs are skipped.

Usage:
  python -I scripts/generate_notes.py --data data/prepared_test47 --hyp outputs/test47-vad-nocond \
      --hyp-separated outputs/test47-vad-nocond-wt --out outputs/notes-qwen3-14b/test47
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I drops the script dir from sys.path
from evaluate import norm_words  # noqa: E402

PROMPT_VERSION = "v3"
# Pilot history (2 consultations): v1 (one prompt, instructions first) made the model echo
# labelled transcripts and add negatives nobody discussed; v2 (transcript first) prefixed every
# line with "Doctor:"; naming example negatives to avoid ("travel", "allergies") made the model
# write exactly those. v3: chat API, rules in the system message, no example negatives.
SYSTEM = """You are a UK general practitioner writing the clinical note for a consultation you just held.
Rules:
- Output only the note, as plain text with short headed sections. Do not repeat or quote the transcript, \
and do not prefix lines with speaker names.
- Use only information stated in the transcript. Do not add findings, values or advice that were not said.
- Record a negative only if that exact point was asked about or stated in the transcript. Do not add \
negatives that were not discussed.
- Sections where they apply: presenting complaint and history, relevant negatives, past medical history, \
drug history and allergies, social history, impression, plan and safety-netting."""
USER = {
    "labelled": "Transcript (each line labelled with who is speaking):\n\n{transcript}",
    "unlabelled": "Transcript from one room microphone (speakers are not labelled; lines may mix the doctor "
                  "and the patient):\n\n{transcript}",
}


def clean(text):
    """Drop PriMock57 annotation tags from reference text."""
    return re.sub(r"\s+", " ", re.sub(r"</?UNSURE>|<[A-Z_]+/>", "", text)).strip()


def turns(channels):
    """Merge two labelled channels into speaker turns.

    channels: {speaker: segments}. With word timestamps, every word of both
    channels is ordered by its start time and a new turn starts whenever the
    speaker changes. Segments without previous-text conditioning can run 30 s or
    more and often have no punctuation, so ordering by segment start (or by
    sentence) puts answers before questions and cuts turns in half.
    Without word timestamps this falls back to whole segments.
    """
    items = []
    for spk, segs in channels.items():
        for s in segs:
            if s.get("words"):
                items += [(w["start"], spk, w["word"]) for w in s["words"]]
            else:
                items.append((s["start"], spk, " " + s["text"].strip()))
    out = []
    for _, spk, w in sorted(items, key=lambda x: x[0]):
        if out and out[-1][0] == spk:
            out[-1][1].append(w)
        else:
            out.append((spk, [w]))
    return [(spk, "".join(ws).strip()) for spk, ws in out]


def unlabelled(source):
    return source.removesuffix("_plain") in ("asr_mixed", "human_unlabelled")


def transcript(source, data_dir, hyp_dir, cid):
    """Transcript text for one source. A "_plain" suffix applies the Whisper
    normaliser to every line (lower case, no punctuation or fillers), so human
    and ASR text can be given to the model in exactly the same form."""
    base = source.removesuffix("_plain")
    if base in ("human", "human_unlabelled"):
        with open(os.path.join(data_dir, cid, "utterances.json")) as f:
            utts = sorted(json.load(f)["utterances"], key=lambda u: u["start"])
        lines = [(u["speaker"], clean(u["raw"])) for u in utts]
    elif base == "asr_separated":
        channels = {}
        for spk in ("doctor", "patient"):
            with open(os.path.join(hyp_dir, cid, f"{spk}.json")) as f:
                channels[spk] = json.load(f)["segments"]
        lines = turns(channels)
    elif base == "asr_mixed":
        with open(os.path.join(hyp_dir, cid, "mixed.json")) as f:
            lines = [(None, s["text"].strip()) for s in json.load(f)["segments"]]
    else:
        raise ValueError(source)
    if source.endswith("_plain"):
        lines = [(spk, " ".join(norm_words(t))) for spk, t in lines]
    lines = [(spk, t) for spk, t in lines if t]
    if unlabelled(source):
        return "\n".join(t for _, t in lines)
    return "\n".join(f"{spk.capitalize()}: {t}" for spk, t in lines)


def ollama(url, model, user, num_ctx):
    body = {"model": model, "stream": False, "think": False,
            "options": {"temperature": 0, "seed": 0, "num_ctx": num_ctx},
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]}
    req = urllib.request.Request(f"{url}/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="prepared folder (utterances.json per consultation)")
    ap.add_argument("--hyp", required=True, help="transcribe.py output with doctor, patient and mixed")
    ap.add_argument("--hyp-separated", help="use this transcribe.py output for asr_separated instead of --hyp "
                                            "(e.g. a run with --word-timestamps)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sources", nargs="+", default=["human", "asr_separated", "asr_mixed"])
    ap.add_argument("--model", default="qwen3:14b")
    ap.add_argument("--num-ctx", type=int, default=16384)
    ap.add_argument("--ollama", default="http://127.0.0.1:11434")
    ap.add_argument("--ids", nargs="*")
    args = ap.parse_args()

    ids = sorted(d for d in os.listdir(args.data) if os.path.isfile(os.path.join(args.data, d, "utterances.json")))
    if args.ids:
        ids = [i for i in ids if i in set(args.ids)]
    for cid in ids:
        os.makedirs(os.path.join(args.out, cid), exist_ok=True)
        for source in args.sources:
            path = os.path.join(args.out, cid, f"{source}.json")
            if os.path.exists(path):
                continue
            hyp_dir = args.hyp_separated if source.startswith("asr_separated") and args.hyp_separated else args.hyp
            text = transcript(source, args.data, hyp_dir, cid)
            user = USER["unlabelled" if unlabelled(source) else "labelled"].format(transcript=text)
            t0 = time.time()
            r = ollama(args.ollama, args.model, user, args.num_ctx)
            if r.get("prompt_eval_count", 0) >= args.num_ctx:
                print(f"warning: {cid}/{source} prompt filled the {args.num_ctx}-token context; raise --num-ctx")
            note = re.sub(r"<think>.*?</think>", "", r["message"]["content"], flags=re.S).strip()
            if len(re.findall(r"^(Doctor|Patient):", note, flags=re.M)) > 3:
                print(f"warning: {cid}/{source} note seems to repeat the transcript")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"id": cid, "source": source, "model": args.model, "prompt_version": PROMPT_VERSION,
                           "hyp": None if source == "human" else hyp_dir, "note": note,
                           "prompt_tokens": r.get("prompt_eval_count"), "output_tokens": r.get("eval_count"),
                           "runtime_s": round(time.time() - t0, 1)}, f, indent=1, ensure_ascii=False)
            print(f"{cid}/{source}: {r.get('prompt_eval_count')} prompt tokens, {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
