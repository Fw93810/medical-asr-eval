"""What happens to negation words ("no", "not", "never", "nothing", ...) in ASR output?

For every reference negation word (all of the audio, not only overlaps) this
records whether the ASR got it right, deleted it, or substituted it, and with
what ("no" -> "know"), and whether it repeats the previous negation ("no no
allergies", where losing one copy keeps the meaning). It also counts
hypothesis negations that replace a non-negation reference word (a negation
the speaker did not say).
Negations are split into clinical ("no fever") and discourse markers ("no, okay")
with the same rule as analyze_overlap.py.

Writes to --out:
  negation_words.csv   one row per reference negation word, with outcome and context
  negation_pairs.csv   substitution pairs involving a negation, with counts
  negation_summary.csv per run x condition x class: counts and rates

Usage:
  python -I scripts/analyze_negations.py --data data/prepared_test47 \
      --hyp outputs/test47-vad-nocond outputs/test47-parakeet-local --out results/test47/negations
"""
import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # -I drops the script dir from sys.path
import jiwer  # noqa: E402
from analyze_overlap import NEGATION, word_class  # noqa: E402
from evaluate import norm_words  # noqa: E402


def ref_words(data_dir, cid, cond):
    with open(os.path.join(data_dir, cid, "utterances.json")) as f:
        utts = sorted(json.load(f)["utterances"], key=lambda u: u["start"])
    words, classes = [], []
    for u in utts:
        if cond != "mixed" and u["speaker"] != cond:
            continue
        ws = norm_words(u["text"])
        words += ws
        classes += [word_class(ws, k) for k in range(len(ws))]
    return words, classes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--hyp", nargs="+", required=True, help="transcribe.py output folders")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    rows, pairs, introduced = [], Counter(), Counter()
    for hyp_dir in args.hyp:
        run = os.path.basename(os.path.normpath(hyp_dir))
        for cid in sorted(os.listdir(hyp_dir)):
            for cond in ("doctor", "patient", "mixed"):
                path = os.path.join(hyp_dir, cid, f"{cond}.json")
                if not os.path.isfile(path):
                    continue
                ref, cls = ref_words(args.data, cid, cond)
                with open(path) as f:
                    hyp = [w for s in json.load(f)["segments"] for w in norm_words(s["text"])] or ["<empty>"]
                out = jiwer.process_words(" ".join(ref), " ".join(hyp))
                for c in out.alignments[0]:
                    if c.type == "insert":
                        continue
                    for k, i in enumerate(range(c.ref_start_idx, c.ref_end_idx)):
                        j = c.hyp_start_idx + k if c.type != "delete" else None
                        h = hyp[j] if j is not None else ""
                        if c.type == "substitute" and h in NEGATION and ref[i] not in NEGATION:
                            introduced[(run, cond, ref[i], h)] += 1
                        if ref[i] not in NEGATION:
                            continue
                        outcome = {"equal": "correct", "substitute": "substituted", "delete": "deleted"}[c.type]
                        if outcome == "substituted":
                            pairs[(run, cond, ref[i], h, cls[i])] += 1
                        rows.append({
                            "run": run, "id": cid, "condition": cond, "word": ref[i], "class": cls[i],
                            "outcome": outcome, "hyp_word": h,
                            "negation_kept": int(outcome == "correct" or h in NEGATION),
                            # "no no no allergies": losing one of the repeats does not change the meaning
                            "repeat": int(i > 0 and ref[i - 1] in NEGATION),
                            "ref_context": " ".join(ref[max(0, i - 4):i]) + " [" + ref[i] + "] "
                                           + " ".join(ref[i + 1:i + 5]),
                            "hyp_context": "" if j is None else " ".join(hyp[max(0, j - 4):j]) + " [" + h + "] "
                                                                + " ".join(hyp[j + 1:j + 5]),
                        })

    def write(name, data):
        if data:
            with open(os.path.join(args.out, name), "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
                w.writeheader()
                w.writerows(data)

    write("negation_words.csv", rows)
    write("negation_pairs.csv", [
        {"run": r, "condition": c, "ref": a, "hyp": b, "class": k, "count": n}
        for (r, c, a, b, k), n in pairs.most_common()] + [
        {"run": r, "condition": c, "ref": a, "hyp": b, "class": "introduced_negation", "count": n}
        for (r, c, a, b), n in introduced.most_common()])

    groups = defaultdict(list)
    for r in rows:
        groups[(r["run"], r["condition"], r["class"])].append(r)
    summary = []
    for (run, cond, cl), rs in sorted(groups.items()):
        n = len(rs)
        summary.append({
            "run": run, "condition": cond, "class": cl, "n": n,
            "deleted": round(sum(r["outcome"] == "deleted" for r in rs) / n, 4),
            "substituted": round(sum(r["outcome"] == "substituted" for r in rs) / n, 4),
            "substituted_to_non_negation": round(sum(r["outcome"] == "substituted" and not r["negation_kept"]
                                                     for r in rs) / n, 4),
            "negation_lost": round(1 - sum(r["negation_kept"] for r in rs) / n, 4),
            "lost_not_repeat": round(sum(not r["negation_kept"] and not r["repeat"] for r in rs) / n, 4),
            "introduced_negations": sum(v for (r2, c2, _, _), v in introduced.items() if r2 == run and c2 == cond),
        })
    write("negation_summary.csv", summary)

    for s in summary:
        print(f"{s['run']:<24} {s['condition']:<8} {s['class']:<19} n={s['n']:<5} deleted {s['deleted']:.1%}"
              f"  substituted {s['substituted']:.1%} (to non-negation {s['substituted_to_non_negation']:.1%})"
              f"  lost {s['negation_lost']:.1%} (not a repeat {s['lost_not_repeat']:.1%})")
    print("\nmost common substitutions of clinical negations:")
    for (r, c, a, b, k), n in pairs.most_common():
        if k == "negation_clinical" and n >= 2:
            print(f"  {r} {c}: {a} -> {b}  x{n}")


if __name__ == "__main__":
    main()
