"""Heatmap of the note grid: change in fact recall against the note written from the
human transcript, per generation model (rows) and transcript source (columns),
with the paired-bootstrap 95% interval in each cell and the noise floor next to it.

Recall on stated facts is the default (reads <grid>/all/paired_summary_stated.csv,
writes heatmap_stated.svg / .csv); --all-facts uses recall on all facts
(paired_summary.csv -> heatmap.svg / .csv). The regeneration noise in the footnote
comes from <grid>/regeneration_noise.csv (recall_definitions.py --regen).
Plain SVG, no plotting library.

Usage:
  python -I scripts/plot_grid_heatmap.py --grid results/notes/grid
"""
import argparse
import csv
import os

MODELS = [("qwen3-14b", "Qwen3 14B (2025)"), ("qwen3.8-27b", "Qwen3.8-27B (2026)"),
          ("gpt-oss-120b", "gpt-oss-120b (2025)"), ("pooled", "All three")]
SOURCES = [("human_plain", "Human transcript,", "normalised"), ("asr_mixed", "Whisper large-v3,", "mixed channel"),
           ("asr_mixed_qwen3asr", "Qwen3-ASR-1.7B,", "mixed channel")]
NOISE = ("human_rejudge", "Same note,", "judged again")
LIMIT = 3.0  # percentage points at full colour
# diverging pair from the dataviz palette: red (loss) <-> gray <-> blue (gain)
RED, NEUTRAL, BLUE = (0xE3, 0x49, 0x48), (0xF0, 0xEF, 0xEC), (0x2A, 0x78, 0xD6)
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#d6d5d0"


def num(v, places=1):
    """Signed number with a true minus sign (a hyphen is hard to see at small sizes)."""
    return f"{v:+.{places}f}".replace("-", "−")


def fill(v):
    t = min(abs(v) / LIMIT, 1.0) * 0.7  # cap the strength so dark text stays readable
    pole = BLUE if v > 0 else RED
    return "#%02x%02x%02x" % tuple(round(n + (p - n) * t) for n, p in zip(NEUTRAL, pole))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", required=True)
    ap.add_argument("--all-facts", action="store_true", help="recall on all facts instead of stated facts")
    args = ap.parse_args()
    suffix = "" if args.all_facts else "_stated"
    what = "all clinician facts" if args.all_facts else "facts said in the consultation"
    with open(os.path.join(args.grid, "all", f"paired_summary{suffix}.csv"), newline="", encoding="utf-8-sig") as f:
        rows = {(r["vs"], r["source"]): r for r in csv.DictReader(f)}
    with open(os.path.join(args.grid, "regeneration_noise.csv"), newline="", encoding="utf-8-sig") as f:
        regen = {r["facts"]: r for r in csv.DictReader(f)}["all" if args.all_facts else "stated"]

    cells, table = {}, []
    for m, _ in MODELS:
        for s, *_ in SOURCES + [NOISE]:
            r = rows.get((f"{m}/human", f"{m}/{s}"))
            if r is None:
                continue
            lo, hi = (100 * float(x) for x in r["recall_diff_ci95"].split(".."))
            v = 100 * float(r["recall_diff"])
            cells[(m, s)] = (v, lo, hi)
            table.append({"model": m, "source": s, "recall_diff_points": round(v, 1),
                          "ci95_low": round(lo, 1), "ci95_high": round(hi, 1), "excludes_zero": lo > 0 or hi < 0})

    cw, ch, left, top, gap = 150, 58, 170, 118, 2
    noise_x = left + len(SOURCES) * cw + 28
    width, height = noise_x + cw + 24, top + len(MODELS) * ch + 128
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
           f'font-family="Inter, Segoe UI, Helvetica, Arial, sans-serif">',
           f'<rect width="{width}" height="{height}" fill="{SURFACE}"/>',
           f'<text x="16" y="28" font-size="15" font-weight="600" fill="{INK}">Change in fact recall vs the note written '
           f'from the human transcript</text>',
           f'<text x="16" y="47" font-size="12" fill="{INK2}">Recall on {what}; percentage points; '
           f'25 test consultations</text>',
           f'<text x="16" y="63" font-size="12" fill="{INK2}">Paired bootstrap 95% interval; '
           f'bold = interval excludes 0</text>']
    for k, (s, l1, l2) in enumerate(SOURCES + [NOISE]):
        x = (left + k * cw if k < len(SOURCES) else noise_x) + cw / 2
        for j, t in enumerate((l1, l2)):
            out.append(f'<text x="{x}" y="{top - 26 + 14 * j}" font-size="12" text-anchor="middle" fill="{INK2}">{t}</text>')
    out.append(f'<text x="{noise_x + cw / 2}" y="{top - 44}" font-size="11" text-anchor="middle" fill="{INK2}" '
               f'font-style="italic">noise floor</text>')
    for i, (m, name) in enumerate(MODELS):
        y = top + i * ch + (10 if m == "pooled" else 0)
        out.append(f'<text x="{left - 12}" y="{y + ch / 2 + 4}" font-size="12.5" text-anchor="end" '
                   f'fill="{INK}" font-weight="{600 if m == "pooled" else 400}">{name}</text>')
        for k, (s, *_) in enumerate(SOURCES + [NOISE]):
            if (m, s) not in cells:
                continue
            v, lo, hi = cells[(m, s)]
            x = left + k * cw if k < len(SOURCES) else noise_x
            sig = lo > 0 or hi < 0
            out.append(f'<rect x="{x + gap / 2}" y="{y + gap / 2}" width="{cw - gap}" height="{ch - gap}" rx="4" '
                       f'fill="{fill(v)}"><title>{name} / {s}: {num(v)} [{num(lo)}, {num(hi)}]</title></rect>')
            out.append(f'<text x="{x + cw / 2}" y="{y + ch / 2 - 2}" font-size="15" text-anchor="middle" fill="{INK}" '
                       f'font-weight="{700 if sig else 400}">{num(v)}</text>')
            out.append(f'<text x="{x + cw / 2}" y="{y + ch / 2 + 15}" font-size="11" text-anchor="middle" '
                       f'fill="{INK2}">[{num(lo)}, {num(hi)}]</text>')
    # scale legend
    ly = top + len(MODELS) * ch + 34
    steps = 13
    for j in range(steps):
        v = -LIMIT + 2 * LIMIT * j / (steps - 1)
        out.append(f'<rect x="{left + j * 22}" y="{ly}" width="22" height="10" fill="{fill(v)}"/>')
    for v, anchor in ((-LIMIT, "start"), (0, "middle"), (LIMIT, "end")):
        x = left + (v + LIMIT) / (2 * LIMIT) * steps * 22
        out.append(f'<text x="{x}" y="{ly + 25}" font-size="11" text-anchor="{anchor}" fill="{INK2}">'
                   f'{num(v, 0) if v else "0"}</text>')
    out.append(f'<text x="{left - 12}" y="{ly + 9}" font-size="11" text-anchor="end" fill="{INK2}">fewer facts</text>')
    out.append(f'<text x="{left + steps * 22 + 10}" y="{ly + 9}" font-size="11" fill="{INK2}">more facts</text>')
    lo, hi = (100 * float(x) for x in regen["recall_diff_ci95"].split(".."))
    out.append(f'<text x="16" y="{ly + 52}" font-size="11" fill="{INK2}">Noise floor for every cell: regenerating the '
               f'same Qwen3 14B notes on a different GPU gives {num(100 * float(regen["recall_diff"]))} '
               f'[{num(lo)}, {num(hi)}] points, with {100 * float(regen["label_changed_rate"]):.1f}% of fact labels '
               f'changed.</text>')
    out.append(f'<text x="16" y="{ly + 68}" font-size="11" fill="{INK2}">"Same note, judged again": '
               f'10 consultations.</text>')
    out.append("</svg>")
    with open(os.path.join(args.grid, f"heatmap{suffix}.svg"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    with open(os.path.join(args.grid, f"heatmap{suffix}.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(table[0].keys()))
        w.writeheader()
        w.writerows(table)
    print(f"wrote {args.grid}/heatmap{suffix}.svg, {len(cells)} cells")


if __name__ == "__main__":
    main()
