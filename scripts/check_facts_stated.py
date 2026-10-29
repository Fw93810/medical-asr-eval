"""Which facts of the clinician's note were actually said in the consultation?

A generated note can only contain what was said. Facts the clinician added from
elsewhere (examination findings, their own reasoning, details never voiced) are
"missing" in every generated note, whatever the transcript quality. And where
the conversation contradicts the clinician's note (said "three to four days",
wrote "3-5 days"), a faithful note is marked "contradicted".

For each consultation this gives Claude (same CLI settings as judge_notes.py) the
reference transcript and the fact list from judge_notes.py, and asks per fact:
  stated      said in the conversation (by either speaker)
  partly      the topic was discussed but a detail of the fact was not said
  not_stated  not discussed at all
plus conflicts = true when what was said is incompatible with the fact.

Writes <judged>/stated/<cid>.json and <judged>/facts_stated.csv.

Usage:
  python -I scripts/check_facts_stated.py --data data/prepared_test47 --judged results/notes/test47
"""
import argparse
import csv
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # -I drops the script dir from sys.path
from generate_notes import transcript  # noqa: E402
from judge_notes import claude, read_json, write_json  # noqa: E402

PROMPT = """Below is the transcript of a GP consultation and a numbered list of facts taken from the \
note the GP wrote afterwards. For each fact, decide whether it was said in the conversation:
- "stated": the fact was said by the doctor or the patient (wording may differ),
- "partly": the topic was discussed but a detail of the fact (a number, a duration, a side, a qualifier) \
was not said,
- "not_stated": it was not discussed (for example an examination finding, the GP's own reasoning, or a \
detail that never came up).
Also set "conflicts" to true when what was said in the conversation is incompatible with the fact \
(for example the transcript says three to four days and the fact says 3-5 days).

Transcript:
{transcript}

Facts:
{facts}
"""
SCHEMA = {"type": "object", "required": ["facts"], "properties": {"facts": {"type": "array", "items": {
    "type": "object", "required": ["n", "status", "conflicts"], "properties": {
        "n": {"type": "integer"}, "status": {"type": "string", "enum": ["stated", "partly", "not_stated"]},
        "conflicts": {"type": "boolean"}, "evidence": {"type": "string"}}}}}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--judged", required=True, help="judge_notes.py output folder (uses its facts/)")
    ap.add_argument("--model", default="opus")
    ap.add_argument("--claude", default=os.environ.get("CLAUDE_BIN", "claude"), help="Claude Code CLI (default: $CLAUDE_BIN or claude on PATH)")
    args = ap.parse_args()

    rows = []
    for path in sorted(glob.glob(os.path.join(args.judged, "facts", "*.json"))):
        cid = os.path.splitext(os.path.basename(path))[0]
        facts = read_json(path)["facts"]
        out = os.path.join(args.judged, "stated", f"{cid}.json")
        if not os.path.exists(out):
            listing = "\n".join(f"{i}. {f['fact']}" for i, f in enumerate(facts, 1))
            answer, models = claude(args, PROMPT.format(transcript=transcript("human", args.data, None, cid),
                                                        facts=listing), SCHEMA)
            write_json(out, {"id": cid, "models": models, **answer})
            print(f"stated {cid}")
        by_n = {x["n"]: x for x in read_json(out)["facts"]}
        for i, f in enumerate(facts, 1):
            s = by_n.get(i, {"status": "not_stated", "conflicts": False, "evidence": "(no label returned)"})
            rows.append({"id": cid, "n": i, "fact": f["fact"], "category": f["category"], "negative": f["negative"],
                         "status": s["status"], "conflicts": s["conflicts"], "evidence": s.get("evidence", "")})

    with open(os.path.join(args.judged, "facts_stated.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    n = len(rows)
    for st in ("stated", "partly", "not_stated"):
        print(f"{st}: {sum(r['status'] == st for r in rows) / n:.1%}")
    print(f"conflicts with the conversation: {sum(r['conflicts'] for r in rows) / n:.1%}")


if __name__ == "__main__":
    main()
