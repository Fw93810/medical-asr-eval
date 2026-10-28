"""Attribute note-level errors to the ASR error types around each fact.

For every stated fact, the transcript quote that supports it (the `evidence` column of
facts_stated.csv) is located in the human transcript: the utterance whose words cover the
most of the quote. The ASR's errors inside that utterance's time span (from
error_composition.py's error_ops.csv) give a deletion rate and a substitution rate for
the stretch the fact was said in.

Facts are then grouped by what happened in the note, relative to the human-transcript note
of the same generation model:
  kept          present in both notes (control)
  lost          present in the human note, missing from the ASR note
  contradicted  not contradicted in the human note, contradicted in the ASR note
If ASR deletions cause missing facts, `lost` facts should sit in stretches with far higher
deletion rates than `kept` facts; if substitutions cause contradictions, `contradicted`
facts should sit in stretches with more substitutions.

Heuristic limits: the quote is matched to one utterance by word overlap (quotes that cover
under half their words are left unlocated); in the mixed channel, errors on the other
speaker's overlapping words fall in the same time span.

Writes to --out: fact_attribution.csv (one row per fact per ASR source) and
attribution_summary.csv (per source and group).

Usage:
  python -I scripts/attribute_note_errors.py --labels results/notes/stress/qwen3.8-27b/fact_labels.csv \
      --stated results/notes/test47/facts_stated.csv --data data/prepared_test47 \
      --source asr_mixed_s3_snr0_whisper=results/stress/test47/s3_snr0/composition/error_ops.csv:s3_snr0-whisper \
      --out results/notes/stress/qwen3.8-27b/attribution
"""
import argparse
import csv
import json
import os
import statistics
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I drops the script dir from sys.path
from evaluate import norm_words  # noqa: E402

STRETCH_DELETED = 0.5  # a fact's utterance counts as dropped when at least half its words are deleted


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def locate(evidence, utts):
    """Best-covering utterance for a quote: (start, end, ref words, coverage) or None."""
    q = Counter(norm_words(evidence))
    if not q:
        return None
    best = None
    for u in utts:
        cover = sum((q & u["bag"]).values()) / sum(q.values())
        if best is None or cover > best[3]:
            best = (u["start"], u["end"], u["n"], cover)
    return best if best and best[3] >= 0.5 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True, help="judge_notes.py fact_labels.csv with human and ASR sources")
    ap.add_argument("--stated", required=True, help="facts_stated.csv (status and transcript evidence per fact)")
    ap.add_argument("--data", required=True, help="prepared folder with utterances.json per consultation")
    ap.add_argument("--source", action="append", required=True,
                    help="<note source>=<error_ops.csv>:<run name>, repeatable")
    ap.add_argument("--human", default="human")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    stated = {(r["id"], r["n"]): r for r in read_csv(args.stated) if r["status"] == "stated"}
    labels = defaultdict(dict)  # source -> (id, n) -> label
    for r in read_csv(args.labels):
        if (r["id"], r["n"]) in stated:
            labels[r["source"]][(r["id"], r["n"])] = r["label"]
    utts = {}
    for cid in {k[0] for k in stated}:
        path = os.path.join(args.data, cid, "utterances.json")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                utts[cid] = [{"start": u["start"], "end": u["end"], "n": len(norm_words(u["text"])),
                              "bag": Counter(norm_words(u["text"]))} for u in json.load(f)["utterances"]]
    where = {k: locate(r["evidence"], utts.get(k[0], [])) for k, r in stated.items()}

    rows, summary = [], []
    for spec in args.source:
        source, rest = spec.split("=", 1)
        ops_path, run = rest.rsplit(":", 1)
        ops = defaultdict(list)  # id -> [(t, op)]
        for r in read_csv(ops_path):
            if r["run"] == run and r["condition"] == "mixed" and r["op"] in ("del", "sub"):
                ops[r["id"]].append((float(r["t"]), r["op"]))
        groups = defaultdict(list)
        for key, asr_label in labels[source].items():
            hum = labels[args.human].get(key)
            if hum is None:
                continue
            if hum == "present" and asr_label == "present":
                group = "kept"
            elif hum == "present" and asr_label == "missing":
                group = "lost"
            elif hum != "contradicted" and asr_label == "contradicted":
                group = "contradicted"
            else:
                continue
            loc = where[key]
            row = {"source": source, "id": key[0], "n": key[1], "group": group, "human_label": hum,
                   "asr_label": asr_label, "fact": stated[key]["fact"], "evidence": stated[key]["evidence"]}
            if loc and loc[2]:
                start, end, n_words, cover = loc
                inside = [op for t, op in ops[key[0]] if start <= t <= end]
                row.update({"utt_start": start, "utt_end": end, "utt_words": n_words, "coverage": round(cover, 2),
                            "del_rate": round(inside.count("del") / n_words, 3),
                            "sub_rate": round(inside.count("sub") / n_words, 3)})
                groups[group].append(row)
            rows.append(row)
        for group in ("kept", "lost", "contradicted"):
            g = groups[group]
            total = sum(1 for r in rows if r["source"] == source and r["group"] == group)
            summary.append({
                "source": source, "group": group, "facts": total, "located": len(g),
                "mean_del_rate": round(statistics.mean(r["del_rate"] for r in g), 3) if g else "",
                "mean_sub_rate": round(statistics.mean(r["sub_rate"] for r in g), 3) if g else "",
                "share_stretch_deleted": round(sum(r["del_rate"] >= STRETCH_DELETED for r in g) / len(g), 3) if g else "",
                "share_with_substitution": round(sum(r["sub_rate"] > 0 for r in g) / len(g), 3) if g else ""})

    os.makedirs(args.out, exist_ok=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(os.path.join(args.out, "fact_attribution.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(args.out, "attribution_summary.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0]))
        w.writeheader()
        w.writerows(summary)
    for s in summary:
        print(s)


if __name__ == "__main__":
    main()
