"""Judge generated notes against the clinician's note, blind to how each note was made.

Two steps, both through the Claude Code CLI in non-interactive mode (`claude -p`,
no tools, JSON-schema output), so the judging is scripted and repeatable:

  1. facts:  split each PriMock57 clinician note into atomic facts, once per
             consultation, so every candidate note is scored against the same list.
  2. judge:  for each candidate note, mark every fact as present / missing /
             contradicted, and list the candidate's own clinical claims that the
             clinician's note contradicts or does not mention.

The judge sees only the fact list and the candidate note: never the source
(human / asr_separated / asr_mixed) or the transcript. Jobs run in a shuffled
order (fixed seed). Results are grouped by source only afterwards.

Writes to --out:
  facts/<cid>.json          step 1 output
  judged/<cid>__<source>.json   step 2 output (raw judge answer + model id)
  scores.csv                one row per note
  fact_labels.csv           one row per fact per note (for spot checks)
  summary.csv               per source: fact recall, contradictions, unsupported claims
  spotcheck.csv             random notes with the judge's labels and an empty column for yours

Usage:
  python -I scripts/judge_notes.py --notes outputs/notes-qwen3-14b/test47 --gold data/primock57/notes \
      --out results/notes/test47
"""
import argparse
import csv
import glob
import json
import os
import random
import subprocess
import tempfile
import time
from collections import defaultdict

SYSTEM = ("You are a careful clinical documentation reviewer. You compare medical notes precisely, "
          "judge meaning rather than wording, and answer only in the requested JSON format.")

FACTS_PROMPT = """Split this GP's clinical note into atomic clinical facts: one checkable statement each \
(a symptom with its duration, a relevant negative, a medication, an allergy status, a social history item, \
the impression, each plan item). Expand abbreviations (e.g. "3/7" = 3 days, "nil" = no, "PMH" = past medical history). \
Mark relevant negatives ("no blood in stool", "nil smoking") with negative = true.

Clinician's note:
{note}
"""
FACTS_SCHEMA = {"type": "object", "required": ["facts"], "properties": {"facts": {"type": "array", "items": {
    "type": "object", "required": ["fact", "category", "negative"], "properties": {
        "fact": {"type": "string"},
        "category": {"type": "string", "enum": ["history", "negative_finding", "past_history", "medication",
                                                 "allergy", "social", "impression", "plan", "other"]},
        "negative": {"type": "boolean"}}}}}}

JUDGE_PROMPT = """Below is a numbered list of facts from a reference clinical note, and a candidate note \
written for the same consultation.

1. For each reference fact, decide whether the candidate note:
   - "present": states it (same meaning; wording and abbreviations may differ; for durations and numbers \
the value must match),
   - "missing": does not mention it,
   - "contradicted": states something incompatible (for example a negative turned positive, a different \
duration, a different drug).
2. List clinical claims in the candidate note that are not among the reference facts. For each, say whether \
the reference facts contradict it ("contradicts") or just do not mention it ("not_mentioned"). Ignore \
generic wording, headings and routine safety-netting phrases.

Reference facts:
{facts}

Candidate note:
{note}
"""
JUDGE_SCHEMA = {"type": "object", "required": ["facts", "extra_claims"], "properties": {
    "facts": {"type": "array", "items": {"type": "object", "required": ["n", "label"], "properties": {
        "n": {"type": "integer"}, "label": {"type": "string", "enum": ["present", "missing", "contradicted"]},
        "evidence": {"type": "string"}}}},
    "extra_claims": {"type": "array", "items": {"type": "object", "required": ["claim", "kind"], "properties": {
        "claim": {"type": "string"}, "kind": {"type": "string", "enum": ["contradicts", "not_mentioned"]}}}}}}


def claude(args, prompt, schema, attempts=6):
    """One non-interactive Claude Code call with no tools; returns (parsed JSON, model ids).

    Retries with a growing wait when the service is overloaded or rate-limited.
    """
    cmd = [args.claude, "-p", "--output-format", "json", "--model", args.model, "--tools", "",
           "--json-schema", json.dumps(schema), "--system-prompt", SYSTEM,
           "--no-session-persistence", "--strict-mcp-config"]
    for attempt in range(1, attempts + 1):
        with tempfile.TemporaryDirectory() as empty:  # no project files or CLAUDE.md in reach
            p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8", cwd=empty,
                               timeout=600)
        try:
            out = json.loads(p.stdout)
        except json.JSONDecodeError:
            out = {"is_error": True, "result": (p.stdout + p.stderr)[-300:]}
        if not out.get("is_error"):
            break
        msg = str(out.get("result"))
        transient = any(s in msg for s in ("529", "Overloaded", "overloaded", "429", "rate limit", "500", "503"))
        if not transient or attempt == attempts:
            raise RuntimeError(f"claude -p failed: {msg}")
        wait = 60 * attempt
        print(f"  transient error ({msg[:60]}...), retry {attempt}/{attempts - 1} in {wait}s")
        time.sleep(wait)
    answer = out.get("structured_output")
    if answer is None:
        answer = json.loads(out["result"])
    return answer, sorted(out.get("modelUsage", {}))


def read_json(path):
    with open(path, encoding="utf-8-sig") as f:  # tolerate a BOM (files written by Windows PowerShell)
        return json.load(f)


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)


def write_csv(path, rows):
    if rows:
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--notes", required=True, help="generate_notes.py output folder")
    ap.add_argument("--gold", default="data/primock57/notes")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="opus", help="Claude model for both steps (recorded per call)")
    ap.add_argument("--claude", default=r"D:\Tools\ClaudeCode\claude.exe")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit", type=int, help="judge at most this many notes this run (resumable)")
    ap.add_argument("--spotcheck", type=int, default=20)
    args = ap.parse_args()

    jobs = sorted((os.path.basename(os.path.dirname(p)), os.path.splitext(os.path.basename(p))[0])
                  for p in glob.glob(os.path.join(args.notes, "*", "*.json")))
    random.Random(args.seed).shuffle(jobs)

    done = 0
    for cid, source in jobs:
        facts_path = os.path.join(args.out, "facts", f"{cid}.json")
        if not os.path.exists(facts_path):
            gold = read_json(os.path.join(args.gold, f"{cid}.json"))["note"]
            facts, models = claude(args, FACTS_PROMPT.format(note=gold), FACTS_SCHEMA)
            write_json(facts_path, {"id": cid, "models": models, "gold_note": gold, **facts})
            print(f"facts {cid}: {len(facts['facts'])}")
        judged_path = os.path.join(args.out, "judged", f"{cid}__{source}.json")
        if os.path.exists(judged_path):
            continue
        if args.limit is not None and done >= args.limit:
            break
        facts = read_json(facts_path)["facts"]
        note = read_json(os.path.join(args.notes, cid, f"{source}.json"))["note"]
        listing = "\n".join(f"{i}. {f['fact']}" for i, f in enumerate(facts, 1))
        answer, models = claude(args, JUDGE_PROMPT.format(facts=listing, note=note), JUDGE_SCHEMA)
        write_json(judged_path, {"id": cid, "source": source, "models": models, **answer})
        done += 1
        print(f"judged {done}: {cid}/{source}")

    # collect
    scores, labels = [], []
    for path in sorted(glob.glob(os.path.join(args.out, "judged", "*.json"))):
        j = read_json(path)
        facts = read_json(os.path.join(args.out, "facts", f"{j['id']}.json"))["facts"]
        by_n = {x["n"]: x for x in j["facts"]}
        count = defaultdict(int)
        for i, f in enumerate(facts, 1):
            lab = by_n.get(i, {"label": "missing", "evidence": "(no label returned)"})
            count[lab["label"]] += 1
            if f["negative"]:
                count["neg_" + lab["label"]] += 1
            labels.append({"id": j["id"], "source": j["source"], "n": i, "fact": f["fact"],
                           "category": f["category"], "negative": f["negative"], "label": lab["label"],
                           "evidence": lab.get("evidence", "")})
        n_neg = sum(f["negative"] for f in facts)
        scores.append({
            "id": j["id"], "source": j["source"], "judge_models": " ".join(j["models"]),
            "facts": len(facts), "present": count["present"], "missing": count["missing"],
            "contradicted": count["contradicted"], "negative_facts": n_neg,
            "negative_missing": count["neg_missing"], "negative_contradicted": count["neg_contradicted"],
            "extra_contradicts": sum(c["kind"] == "contradicts" for c in j["extra_claims"]),
            "extra_not_mentioned": sum(c["kind"] == "not_mentioned" for c in j["extra_claims"]),
        })
    os.makedirs(args.out, exist_ok=True)
    write_csv(os.path.join(args.out, "scores.csv"), scores)
    write_csv(os.path.join(args.out, "fact_labels.csv"), labels)

    summary = []
    for source in sorted({s["source"] for s in scores}):
        rs = [s for s in scores if s["source"] == source]
        tot = lambda k: sum(r[k] for r in rs)
        summary.append({
            "source": source, "notes": len(rs), "facts": tot("facts"),
            "recall": round(tot("present") / tot("facts"), 4),
            "missing_rate": round(tot("missing") / tot("facts"), 4),
            "contradicted_rate": round(tot("contradicted") / tot("facts"), 4),
            "negative_facts": tot("negative_facts"),
            "negative_missing_rate": round(tot("negative_missing") / max(1, tot("negative_facts")), 4),
            "negative_contradicted": tot("negative_contradicted"),
            "extra_contradicts_per_note": round(tot("extra_contradicts") / len(rs), 2),
            "extra_not_mentioned_per_note": round(tot("extra_not_mentioned") / len(rs), 2),
        })
    write_csv(os.path.join(args.out, "summary.csv"), summary)

    picked = set(random.Random(args.seed + 1).sample(sorted({(s["id"], s["source"]) for s in scores}),
                                                     min(args.spotcheck, len(scores))))
    write_csv(os.path.join(args.out, "spotcheck.csv"),
              [{**l, "your_label": ""} for l in labels if (l["id"], l["source"]) in picked])
    for s in summary:
        print(s)


if __name__ == "__main__":
    main()
