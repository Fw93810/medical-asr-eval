"""What the note errors are made of: why a clinician fact is missing or contradicted in a
generated note, and what the extra claims are.

Inputs (from judge_notes.py and check_facts_stated.py, in --judged):
  fact_labels.csv   present / missing / contradicted per fact per source
  facts_stated.csv  whether each fact was said in the consultation, and whether the
                    conversation conflicts with it
  judged/*.json     the judge's extra claims per note

Every fact that a note does not contain ("missing" or "contradicted") is put in
the first matching group:
  not_stated          never said in the consultation: no transcript could give it
  reference_conflict  the conversation contradicts the clinician's note itself
  partly_stated       the topic came up but this detail was not said
  shared_omission     said, and also not in the baseline note: the generator's own
                      omission, not caused by this source's transcript
  source_specific     said, and present in the baseline note but not in this one
Each source is compared with its like-for-like baseline (BASELINE below), so
source_specific for asr_mixed_plain vs human_unlabelled_plain is the part that
only the ASR words can explain, and the same number for the controls (human_plain,
human_rejudge) shows how large it is from surface form or judging alone.

Extra claims (in the note, not among the clinician's facts) are split into
contradicts (the clinician's facts say otherwise), added_negative ("no ...",
"denies ...": negatives nobody necessarily asked about) and added_other.

Writes to <judged>/error_composition/: by_category.csv, miss_attribution.csv,
extra_claims.csv, summary.md

Usage:
  python -I scripts/note_error_composition.py --judged results/notes/test47
"""
import argparse
import csv
import glob
import json
import os
import re
from collections import Counter, defaultdict

BASELINE = {"human_rejudge": "human", "human_plain": "human", "human_unlabelled_plain": "human_plain",
            "asr_mixed": "human", "asr_separated": "human", "asr_mixed_plain": "human_unlabelled_plain",
            "asr_separated_plain": "human_plain", "asr_mixed_qwen3asr": "human"}
ORDER = ["human", "human_rejudge", "human_plain", "human_unlabelled_plain", "asr_mixed_plain", "asr_separated_plain",
         "asr_mixed", "asr_mixed_qwen3asr", "asr_separated"]
GROUPS = ["not_stated", "reference_conflict", "partly_stated", "shared_omission", "source_specific"]
NEGATIVE_CLAIM = re.compile(r"^\s*(no|not|nil|none|denies|denied|never|without|non-?)\b|\bno (known|other|recent)\b", re.I)


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def pct(x):
    return f"{100 * x:.1f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judged", required=True)
    args = ap.parse_args()
    out_dir = os.path.join(args.judged, "error_composition")
    os.makedirs(out_dir, exist_ok=True)

    labels = read_csv(os.path.join(args.judged, "fact_labels.csv"))
    stated = {(r["id"], int(r["n"])): r for r in read_csv(os.path.join(args.judged, "facts_stated.csv"))}
    lab = {(r["id"], r["source"], int(r["n"])): r["label"] for r in labels}
    sources = [s for s in ORDER if any(r["source"] == s for r in labels)]

    by_cat, attribution = [], []
    for src in sources:
        rows = [r for r in labels if r["source"] == src]
        n = len(rows)
        groups, groups_neg, n_neg = Counter(), Counter(), 0
        for r in rows:
            key = (r["id"], int(r["n"]))
            st = stated[key]
            neg = r["negative"] == "True"
            n_neg += neg
            if r["label"] == "present":
                continue
            if st["status"] == "not_stated":
                g = "not_stated"
            elif st["conflicts"] == "True":
                g = "reference_conflict"
            elif st["status"] == "partly":
                g = "partly_stated"
            elif src not in BASELINE:
                g = "shared_omission"  # the baseline itself: every stated fact it misses is its own omission
            elif lab.get((r["id"], BASELINE[src], int(r["n"]))) == "present":
                g = "source_specific"
            else:
                g = "shared_omission"
            groups[g] += 1
            groups_neg[g] += neg
        n_stated = sum(stated[(r["id"], int(r["n"]))]["status"] == "stated" for r in rows)
        present_stated = sum(r["label"] == "present" and stated[(r["id"], int(r["n"]))]["status"] == "stated"
                             for r in rows)
        # the reverse of source_specific: said, missing from the baseline note but present here
        gained = sum(1 for r in rows if src in BASELINE and r["label"] == "present"
                     and stated[(r["id"], int(r["n"]))]["status"] == "stated"
                     and stated[(r["id"], int(r["n"]))]["conflicts"] != "True"
                     and lab.get((r["id"], BASELINE[src], int(r["n"]))) != "present")
        attribution.append({
            "source": src, "baseline": BASELINE.get(src, ""), "facts": n,
            "not_present": sum(groups.values()), "not_present_rate": round(sum(groups.values()) / n, 4),
            **{g: groups[g] for g in GROUPS}, **{f"{g}_rate": round(groups[g] / n, 4) for g in GROUPS},
            "source_specific_gained": gained if src in BASELINE else "",
            "net_source_specific_rate": round((groups["source_specific"] - gained) / n, 4) if src in BASELINE else "",
            "recall_on_stated_facts": round(present_stated / n_stated, 4),
            "negative_facts": n_neg, "negative_source_specific": groups_neg["source_specific"],
            "negative_not_stated": groups_neg["not_stated"],
        })
        for cat in sorted({r["category"] for r in rows}):
            c = [r for r in rows if r["category"] == cat]
            c_stated = [r for r in c if stated[(r["id"], int(r["n"]))]["status"] == "stated"]
            by_cat.append({
                "source": src, "category": cat, "facts": len(c),
                "share_of_facts": round(len(c) / n, 4),
                "not_stated_rate": round(sum(stated[(r["id"], int(r["n"]))]["status"] == "not_stated" for r in c) / len(c), 4),
                "missing_rate": round(sum(r["label"] == "missing" for r in c) / len(c), 4),
                "contradicted_rate": round(sum(r["label"] == "contradicted" for r in c) / len(c), 4),
                "recall_on_stated": round(sum(r["label"] == "present" for r in c_stated) / len(c_stated), 4) if c_stated else "",
                "share_of_not_present": round(sum(r["label"] != "present" for r in c)
                                              / max(1, sum(r["label"] != "present" for r in rows)), 4),
            })

    extra = []
    for src in sources:
        claims = Counter()
        notes = 0
        for path in glob.glob(os.path.join(args.judged, "judged", f"*__{src}.json")):
            with open(path, encoding="utf-8-sig") as f:
                j = json.load(f)
            notes += 1
            for c in j["extra_claims"]:
                if c["kind"] == "contradicts":
                    claims["contradicts"] += 1
                elif NEGATIVE_CLAIM.search(c["claim"]):
                    claims["added_negative"] += 1
                else:
                    claims["added_other"] += 1
        extra.append({"source": src, "notes": notes,
                      **{f"{k}_per_note": round(claims[k] / notes, 2) for k in ("contradicts", "added_negative", "added_other")}})

    write_csv(os.path.join(out_dir, "by_category.csv"), by_cat)
    write_csv(os.path.join(out_dir, "miss_attribution.csv"), attribution)
    write_csv(os.path.join(out_dir, "extra_claims.csv"), extra)

    a = {r["source"]: r for r in attribution}
    lines = ["# What the note errors are made of (test set, 47 consultations)", "",
             "Share of the clinician's facts that a note does not contain, by reason:", "",
             "| source (vs baseline) | not in note | never said | conversation contradicts clinician | partly said | "
             "generator omission (shared) | specific to this source (lost / gained) | recall on stated facts |",
             "|---|---|---|---|---|---|---|---|"]
    for s in sources:
        r = a[s]
        spec = (f"{pct(r['source_specific_rate'])} ({r['source_specific']} / {r['source_specific_gained']})"
                if s in BASELINE else "–")
        lines.append(f"| {s}{' (vs ' + BASELINE[s] + ')' if s in BASELINE else ''} | {pct(r['not_present_rate'])} | "
                     f"{pct(r['not_stated_rate'])} | {pct(r['reference_conflict_rate'])} | {pct(r['partly_stated_rate'])} | "
                     f"{pct(r['shared_omission_rate'])} | {spec} | {pct(r['recall_on_stated_facts'])} |")
    lines += ["", "Extra claims per note:", "", "| source | contradicts clinician | added negatives | other additions |",
              "|---|---|---|---|"]
    lines += [f"| {e['source']} | {e['contradicts_per_note']} | {e['added_negative_per_note']} | {e['added_other_per_note']} |"
              for e in extra]
    with open(os.path.join(out_dir, "summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
