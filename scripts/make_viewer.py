"""Build a local HTML viewer: listen to a consultation and compare ASR methods line by line.

For every method folder in --outputs (one transcribe.py output each) and every
<cid>/<condition> in --data, it redoes evaluate.py's normalisation + jiwer
alignment and stores the word-level operations (correct / substitution /
deletion / insertion) with approximate timestamps, so the page can colour the
errors and seek the audio to any word.

Writes one self-contained file, <out>/index.html; the audio is referenced
relatively from --data, so serve the repo root over HTTP, e.g.

  python -I scripts/make_viewer.py --data data/prepared_3min --outputs outputs --out results/viewer
  python -I -m http.server 8765 --bind 127.0.0.1     # then open http://127.0.0.1:8765/results/viewer/
"""
import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # -I drops the script dir from sys.path
import jiwer  # noqa: E402
from evaluate import contains, load_term_extractor, norm_words  # noqa: E402

CONDITIONS = ["doctor", "patient", "mixed"]


def ref_utterances(data_dir, cid, cond):
    with open(os.path.join(data_dir, cid, "utterances.json")) as f:
        utts = json.load(f)["utterances"]
    if cond != "mixed":
        utts = [u for u in utts if u["speaker"] == cond]
    utts = sorted(utts, key=lambda u: u["start"])
    # keep the page consistent with evaluate.py, which reads ref_<cond>.txt
    with open(os.path.join(data_dir, cid, f"ref_{cond}.txt")) as f:
        lines = [l.strip() for l in f if l.strip()]
    if [u["text"].strip() for u in utts] != lines:
        print(f"  warning: {cid}/{cond}: utterances.json differs from ref_{cond}.txt; using the txt lines")
        utts = [{"speaker": cond, "start": 0.0, "end": 0.0, "raw": l, "text": l} for l in lines]
    return utts


def spread(words, start, end):
    """Approximate per-word times by spreading words evenly over [start, end]."""
    n = len(words)
    return [round(start + (k + 0.5) / n * (end - start), 2) for k in range(n)]


def align(utts, segments):
    ref_w, ref_t, ref_row = [], [], []
    for i, u in enumerate(utts):
        ws = norm_words(u["text"])
        ref_w += ws
        ref_t += spread(ws, u["start"], u["end"])
        ref_row += [i] * len(ws)
    hyp_w, hyp_t = [], []
    for s in segments:
        ws = norm_words(s["text"])
        hyp_w += ws
        hyp_t += spread(ws, s["start"], s["end"])
    if not hyp_w:
        hyp_w, hyp_t = ["<empty>"], [0.0]

    out = jiwer.process_words(" ".join(ref_w), " ".join(hyp_w))
    ops = []  # [type, ref word, hyp word, row, time]
    row = 0
    for c in out.alignments[0]:
        if c.type == "insert":
            for j in range(c.hyp_start_idx, c.hyp_end_idx):
                ops.append(["ins", "", hyp_w[j], row, hyp_t[j]])
            continue
        for k, i in enumerate(range(c.ref_start_idx, c.ref_end_idx)):
            row = ref_row[i]
            if c.type == "delete":
                ops.append(["del", ref_w[i], "", row, ref_t[i]])
            else:
                j = c.hyp_start_idx + k
                ops.append(["eq" if c.type == "equal" else "sub", ref_w[i], hyp_w[j], row, hyp_t[j]])
    stats = {"wer": round(out.wer, 4), "sub": out.substitutions, "del": out.deletions,
             "ins": out.insertions, "ref_words": len(ref_w), "hyp_words": len(hyp_w)}
    return ops, stats, ref_w, hyp_w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/prepared_3min")
    ap.add_argument("--outputs", default="outputs", help="folder holding one subfolder per method")
    ap.add_argument("--out", default="results/viewer")
    ap.add_argument("--terms", choices=["auto", "scispacy", "lexicon"], default="lexicon")
    args = ap.parse_args()

    extractor_name, extract_terms = load_term_extractor(args.terms)
    methods = sorted(d for d in os.listdir(args.outputs) if glob.glob(os.path.join(args.outputs, d, "*", "*.json")))
    cids = sorted(d for d in os.listdir(args.data) if os.path.isfile(os.path.join(args.data, d, "utterances.json")))
    os.makedirs(args.out, exist_ok=True)
    audio_rel = os.path.relpath(args.data, args.out).replace(os.sep, "/")

    page = {"methods": [], "items": [], "term_extractor": extractor_name, "audio_base": audio_rel}
    meta = {}
    for cid in cids:
        for cond in CONDITIONS:
            if not os.path.isfile(os.path.join(args.data, cid, f"{cond}.wav")):
                continue
            utts = ref_utterances(args.data, cid, cond)
            ref_terms = extract_terms([u["text"] for u in utts])
            item = {"id": cid, "condition": cond, "audio": f"{cid}/{cond}.wav",
                    "utterances": [{"speaker": u["speaker"], "start": round(u["start"], 2),
                                    "end": round(u["end"], 2), "raw": u["raw"]} for u in utts],
                    "ref_terms": sorted(ref_terms), "methods": {}}
            for m in methods:
                p = os.path.join(args.outputs, m, cid, f"{cond}.json")
                if not os.path.isfile(p):
                    continue
                with open(p) as f:
                    hyp = json.load(f)
                meta.setdefault(m, {"name": m, "backend": hyp["backend"], "model": hyp["model"],
                                    "initial_prompt": hyp.get("initial_prompt") or ""})
                ops, stats, _, hyp_w = align(utts, hyp["segments"])
                stats["missed_terms"] = sorted(t for t in ref_terms if not contains(hyp_w, t.split()))
                stats["runtime_s"], stats["audio_s"] = hyp["runtime_s"], hyp["audio_s"]
                segs = [{"start": round(s["start"], 2), "end": round(s["end"], 2), "text": s["text"].strip()}
                        for s in hyp["segments"]]
                item["methods"][m] = {"stats": stats, "ops": ops, "segments": segs}
            page["items"].append(item)
            print(f"{cid}/{cond}: " + "  ".join(f"{m} {v['stats']['wer']:.3f}" for m, v in item["methods"].items()))
    page["methods"] = [meta[m] for m in methods if m in meta]

    with open(os.path.join(HERE, "viewer_template.html"), encoding="utf-8") as f:
        html = f.read()
    blob = json.dumps(page, ensure_ascii=False).replace("</", "<\\/")
    out_path = os.path.join(args.out, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html.replace("/*__DATA__*/null", blob))
    print(f"wrote {out_path} ({len(page['methods'])} methods, {len(page['items'])} audio files)")


if __name__ == "__main__":
    main()
