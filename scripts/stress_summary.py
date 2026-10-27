"""Collect the stress-test ASR results into one table and draw the figures.

Reads what run_stress_analysis.ps1 wrote under results/stress/<set>/ and writes
  results/stress/<set>/asr_summary.csv   one row per condition x model
  results/stress/<set>/fig_<factor>.svg  corrected WER vs strength, one line per model, 95% intervals
  results/stress/<set>/fig_overlap_came_in.svg  overlap ratio vs deletion rate of the speaker who came in
Plain SVG, same palette as plot_grid_heatmap.py.

Usage:
  python -I scripts/stress_summary.py --set test47
"""
import argparse
import csv
import json
import os

FACTORS = {  # factor -> [(level, x value, x label)]
    "s1_overlap": [("s1_1x", 1, "1x"), ("s1_2x", 2, "2x"), ("s1_3x", 3, "3x")],
    "s3_noise": [("clean", 0, "clean"), ("s3_snr20", 1, "20 dB"), ("s3_snr10", 2, "10 dB"),
                 ("s3_snr5", 3, "5 dB"), ("s3_snr0", 4, "0 dB"), ("s3b_snr10_alarms", 5, "10 dB + alarms")],
}
MODELS = [("whisper", "Whisper large-v3", "#2a78d6"), ("qwen3asr", "Qwen3-ASR-1.7B", "#eb6834")]  # palette slots 1, 2
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#d6d5d0"


def read_csv(path):
    if not os.path.isfile(path):
        return []
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def mixed_row(path):
    return next((r for r in read_csv(path) if r["condition"] == "mixed"), None)


def collect(root, level, model):
    run = f"{level}-{model}"
    raw, eq = mixed_row(f"{root}/runs/{run}/summary.csv"), mixed_row(f"{root}/equiv/{run}/summary.csv")
    if raw is None or eq is None:
        return None
    n = int(raw["ref_words"])
    row = {"level": level, "model": model, "consultations": raw["n_consultations"], "ref_words": n,
           "wer": float(raw["corpus_wer"]), "wer_corrected": float(eq["corpus_wer"]),
           "sub_rate": int(raw["substitutions"]) / n, "del_rate": int(raw["deletions"]) / n,
           "ins_rate": int(raw["insertions"]) / n, "sec_per_audio_min": float(raw["sec_per_audio_min"])}
    roles = {r["run"]: r for r in read_csv(f"{root}/{level}/overlap_roles.csv")}.get(run, {})
    for g in ("out_of_overlap", "in_overlap", "came_in", "holding"):
        row[f"del_rate_{g}"] = float(roles[f"del_rate_{g}"]) if roles.get(f"del_rate_{g}") else ""
    for r in read_csv(f"{root}/{level}/bootstrap/per_run.csv"):
        if r["run"] == run:
            row[r["metric"]] = float(r["value"])
            row[f"{r['metric']}_ci95"] = f"{float(r['ci95_low']):.4f}..{float(r['ci95_high']):.4f}"
    rep = next((r for r in read_csv(f"{root}/{level}/repeats/summary.csv")
                if r["run"] == run and r["condition"] == "mixed"), {})
    row["same_word_loops"] = int(rep.get("same_word_loops", 0) or 0)
    row["phrase_loops"] = int(rep.get("phrase_loops", 0) or 0)
    pair = next((r for r in read_csv(f"{root}/{level}/bootstrap/pairwise.csv")
                 if r["metric"] == "wer_corrected"), None)
    if pair:  # run_a is whisper (listed first), so qwen - whisper = -(a - b)
        row["qwen_minus_whisper_wer_corrected"] = -float(pair["diff_a_minus_b"])
        row["qwen_minus_whisper_ci95"] = f"{-float(pair['ci95_high']):.4f}..{-float(pair['ci95_low']):.4f}"
    return row


def line_chart(path, title, subtitle, xs, series, ylabel):
    """series: [(name, colour, [(x, y, lo, hi)])]; y in percent."""
    w, h, left, right, top, bottom = 640, 380, 64, 170, 64, 56
    ys = [v for _, _, pts in series for p in pts for v in p[1:] if v is not None]
    ymax = max(ys) * 1.1 if ys else 1
    xmin, xmax = min(x for x, _ in xs), max(x for x, _ in xs)
    sx = lambda x: left + (x - xmin) / ((xmax - xmin) or 1) * (w - left - right)
    sy = lambda y: h - bottom - y / ymax * (h - top - bottom)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
           f'font-family="Inter, Segoe UI, Helvetica, Arial, sans-serif">',
           f'<rect width="{w}" height="{h}" fill="{SURFACE}"/>',
           f'<text x="16" y="26" font-size="15" font-weight="600" fill="{INK}">{title}</text>',
           f'<text x="16" y="44" font-size="12" fill="{INK2}">{subtitle}</text>']
    step = 5 if ymax > 20 else 2
    t = 0
    while t <= ymax:
        out.append(f'<line x1="{left}" x2="{w - right}" y1="{sy(t)}" y2="{sy(t)}" stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<text x="{left - 8}" y="{sy(t) + 4}" font-size="11" text-anchor="end" fill="{INK2}">{t}%</text>')
        t += step
    for x, lab in xs:
        out.append(f'<text x="{sx(x)}" y="{h - bottom + 20}" font-size="11" text-anchor="middle" fill="{INK2}">{lab}</text>')
    out.append(f'<text x="{left - 48}" y="{top - 10}" font-size="11" fill="{INK2}">{ylabel}</text>')
    for name, colour, pts in series:
        pts = [p for p in pts if p[1] is not None]
        if not pts:
            continue
        for x, y, lo, hi in pts:
            if lo is not None:
                out.append(f'<line x1="{sx(x)}" x2="{sx(x)}" y1="{sy(lo)}" y2="{sy(hi)}" stroke="{colour}" '
                           f'stroke-width="2" stroke-opacity="0.45"/>')
        out.append(f'<polyline fill="none" stroke="{colour}" stroke-width="2" points="'
                   + " ".join(f"{sx(x)},{sy(y)}" for x, y, _, _ in pts) + '"/>')
        for x, y, _, _ in pts:
            out.append(f'<circle cx="{sx(x)}" cy="{sy(y)}" r="4" fill="{colour}" stroke="{SURFACE}" stroke-width="2">'
                       f'<title>{name}: {y:.1f}%</title></circle>')
        x, y, _, _ = pts[-1]
        out.append(f'<text x="{sx(x) + 10}" y="{sy(y) + 4}" font-size="12" fill="{INK}">{name} {y:.1f}%</text>')
    out.append("</svg>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    args = ap.parse_args()
    root = f"results/stress/{args.set}"

    rows = []
    for factor, levels in FACTORS.items():
        for level, _, _ in levels:
            for model, _, _ in MODELS:
                r = collect(root, level, model)
                if r:
                    rows.append({"factor": factor, **r})
    if not rows:
        print("nothing to summarise yet")
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(f"{root}/asr_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {root}/asr_summary.csv ({len(rows)} rows)")

    by = {(r["level"], r["model"]): r for r in rows}
    ci = lambda r, k: tuple(100 * float(v) for v in r[f"{k}_ci95"].split("..")) if r.get(f"{k}_ci95") else (None, None)
    titles = {"s1_overlap": "S1: more doctor-patient overlap", "s3_noise": "S3: background noise (DEMAND babble)"}
    for factor, levels in FACTORS.items():
        series = []
        for model, name, colour in MODELS:
            pts = []
            for level, x, _ in levels:
                r = by.get((level, model))
                if r:
                    lo, hi = ci(r, "wer_corrected")
                    pts.append((x, 100 * r["wer_corrected"], lo, hi))
            series.append((name, colour, pts))
        if any(pts for _, _, pts in series):
            line_chart(f"{root}/fig_{factor}.svg", titles[factor],
                       f"Mixed channel, corrected WER, {args.set}; bars = 95% bootstrap interval over consultations",
                       [(x, lab) for _, x, lab in levels], series, "corrected WER")

    # overlap ratio vs deletion rate of the speaker who came in
    levels_file = f"data/stress/{args.set}/s1_levels.json"
    if os.path.isfile(levels_file):
        ratio = {lv["level"]: lv["overlap_ratio"] for lv in json.load(open(levels_file))["levels"]}
        series = []
        for model, name, colour in MODELS:
            pts = [(100 * ratio[lv], 100 * by[(lv, model)]["del_rate_came_in"], None, None)
                   for lv, _, _ in FACTORS["s1_overlap"] if (lv, model) in by and by[(lv, model)]["del_rate_came_in"] != ""]
            series.append((name, colour, pts))
        xs = [(round(100 * ratio[lv], 1), f"{100 * ratio[lv]:.1f}%") for lv, _, _ in FACTORS["s1_overlap"] if lv in ratio]
        line_chart(f"{root}/fig_overlap_came_in.svg", "S1: deletions of the speaker who came in",
                   f"Overlap ratio (overlap s / speech s) vs deletion rate inside overlap, came_in role, {args.set}",
                   xs, series, "deletion rate")


if __name__ == "__main__":
    main()
