"""Check that two transcribe.py outputs of the same audio agree (e.g. batched vs one chunk at a time).

Compares segment by segment (same chunk plan, so the same segment times) and reports
how many segments differ and the word-level difference after the Whisper normaliser.

Usage:
  python -I scripts/compare_transcripts.py outputs/run-a/<cid>/<cond>.json outputs/run-b/<cid>/<cond>.json
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # -I drops the script dir from sys.path
import jiwer  # noqa: E402
from evaluate import norm_words  # noqa: E402


def main():
    a, b = (json.load(open(p)) for p in sys.argv[1:3])
    sa = {(s["start"], s["end"]): s["text"] for s in a["segments"]}
    sb = {(s["start"], s["end"]): s["text"] for s in b["segments"]}
    keys = sorted(set(sa) | set(sb))
    differ = [k for k in keys if sa.get(k, "") != sb.get(k, "")]
    wa = [w for k in keys for w in norm_words(sa.get(k, ""))]
    wb = [w for k in keys for w in norm_words(sb.get(k, ""))]
    o = jiwer.process_words(" ".join(wa), " ".join(wb))
    print(f"segments: {len(keys)}, differing: {len(differ)}; words {len(wa)} vs {len(wb)}, "
          f"word difference {o.substitutions + o.deletions + o.insertions} ({o.wer:.2%})")
    print(f"runtime {a['runtime_s']}s vs {b['runtime_s']}s")
    for k in differ[:3]:
        print(f"  [{k[0]}-{k[1]}]\n    A: {sa.get(k, '')[:150]}\n    B: {sb.get(k, '')[:150]}")


if __name__ == "__main__":
    main()
