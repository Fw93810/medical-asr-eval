# Stage 3: note grid (generation model × transcript source)

Date: 2026-10-27.

Grid design:
- **Rows**: four transcript sources, all mixed channel.
- **Columns**: three generation models.
- **Sample**: 25 test consultations per cell, listed in `results/notes/test47/grid_ids.txt`, drawn from the 47 test consultations with fixed seed 0.
- **Judging**: the frozen judge v1, with the fact lists already cached for the test set.

## 1. Setup

### Generation models (vertical axis: generation model)

| Generation model | Released | Family / generation | Parameters | Quantisation | Thinking |
|---|---|---|---|---|---|
| Qwen3 14B (`qwen3:14b`) | 2025-04 | Qwen3 | 14.8B, dense | Q4_K_M | Off |
| Qwen3.8-27B (`qwen3.8:27b-q4_K_M`) | 2026-08 | Qwen3.8 (the third major update after Qwen3: 3.5, 3.6, 3.8) | 27.3B, dense | Q4_K_M | Off |
| gpt-oss-120b (`gpt-oss:120b`) | 2025-08 | OpenAI gpt-oss | 117B MoE, 5.1B active | MXFP4 (native) | **Cannot be switched off; set to the lowest effort, `low`** |

**Generation confound**: the three models differ in family, generation and architecture. By public overall rankings, the 2026 Qwen3.8-27B is above the 2025 gpt-oss-120b. The vertical axis is therefore called "generation model", not "model size"; differences between columns cannot be read as an effect of parameter count.

**gpt-oss thinking**: gpt-oss cannot switch thinking off; the lowest setting is `low`. This departs from the "thinking off" rule used for the other two columns.
- The reasoning text is not part of the note; it is recorded separately.
- About 360 characters of reasoning per note (median), at most 1,307.

**Environment**:
- **All three columns were generated with Ollama 0.40.11 on rented A100 80GB GPUs**, through the same `generate_notes.py` and `/api/chat`, with the same generation settings:
  - prompt version v3
  - temperature 0, seed 0
  - context 16384
- **Two machines**:
  - 14B and 27B on one A100 PCIe (system disk only 50 GB);
  - gpt-oss's weights are a single 65 GB file that did not fit there, so it ran on a second A100 SXM4.
  - Both are the same GA100 chip with the same Ollama version.
- **Execution**: `scripts/run_grid.sh`, run with nohup on the server, unaffected by the local network.

**Why the 14B column was regenerated on the server**: the same `qwen3:14b` (weights hash identical to the local copy) wrote notes on the server that were not identical to the earlier local notes. On a different GPU, floating-point differences make greedy decoding diverge at some point. So the old 14B notes from the test-set round were not reused; all three grid columns were generated on A100. The difference between the two generations measures the "regeneration noise" (section 2.2).

### Transcript sources (horizontal axis)

| Row | Contents |
|---|---|
| `human` | Human transcript, with speaker labels |
| `human_plain` | Human transcript passed through the Whisper normaliser (lower case, no punctuation, no fillers): the surface-form-only control |
| `asr_mixed` | Whisper large-v3, mixed channel (`test47-vad-nocond`), no speaker labels |
| `asr_mixed_qwen3asr` | Qwen3-ASR-1.7B, mixed channel, no speaker labels |

**Judge-noise control**: in each column, the `human` notes of 10 consultations were judged a second time, unchanged (`human_rejudge`); the list is `grid_rejudge_ids.txt`.

### Time and usage

| Item | Time |
|---|---|
| Server 1 (14B + 27B, 200 notes) | about 1.4 h; the 27B took about 25 s per note |
| Server 2 (gpt-oss, 100 notes) | about 1 h, about 25 s per note |
| Claude judging | 330 calls |

Judging ran locally through `claude -p`, about 16 s per call, without hitting the usage limit.

## 2. Results

### 2.1 Primary metric: recall on stated facts

| Metric | Numerator | Denominator | Role |
|---|---|---|---|
| **Recall on stated facts** | Facts present in the note | Facts explicitly said in the conversation (`facts_stated.csv` status "stated") | **Primary**, used throughout |
| Recall on all facts | Facts present in the note | All facts in the clinician's note | Supplementary |

**Why stated facts are the primary metric**: about one fifth of the clinician's facts (162 of 725) were never said or only partly said in the conversation. No transcript, however accurate, can let a note contain them. Keeping them in the denominator adds the same "impossible" share to every cell and dilutes the differences between transcript sources and between generation models.

**78.8% and 69.1% do not contradict each other**: the 78.8% reported in the test-set round is recall on stated facts; the 69.1% in the first draft of stage 3 is recall on all facts. The difference comes entirely from the denominator, not from the consultation subset or the generation environment:

| Run | Consultations | Facts | Recall on all facts | Stated facts | **Recall on stated facts** |
|---|---|---|---|---|---|
| Test-set 14B, local RTX 5080, all 47 | 47 | 1408 | 68.3% | 1059 | **78.8%** |
| Test-set 14B, local RTX 5080, the 25 grid consultations | 25 | 725 | 69.1% | 563 | 78.3% |
| Grid 14B, A100 (regenerated) | 25 | 725 | **69.1%** | 563 | **77.6%** |

Script: `scripts/recall_definitions.py`.

### 2.2 Noise floor for every note-level difference

**Regeneration noise**: for the same 25 consultations and the human transcript, the 14B generated notes once on the local RTX 5080 and once on the A100, and both were judged. The difference between the two is the noise of "regenerating once in a different environment":

| Facts | Labels changed | Present → not | Not → present | Recall difference (A100 − local) |
|---|---|---|---|---|
| **Stated facts** (563) | 6.8% | 21 | 17 | **−0.7 [−3.0, +1.6]** |
| All facts (725) | 7.2% | 25 | 25 | 0.0 [−1.9, +1.9] |

**This document takes about ±2 percentage points as the noise floor for every note-level difference.** The paired-bootstrap intervals only reflect sampling over consultations; they do not include the variation from regenerating the note for the same consultation. Therefore:

- a difference of around 2 points is only "comparable to regeneration noise", even if its interval excludes 0;
- only differences clearly beyond the noise floor count as substantive.

**Judge noise**: the same note judged again unchanged (10 consultations per column). Pooled over the three columns, the stated-fact recall difference is +0.2 [−0.7, +1.1], much smaller than the regeneration noise.

Noise-floor data: `results/notes/grid/regeneration_noise.csv`.

### 2.3 Recall per cell

Each cell shows "recall on stated facts / recall on all facts", with contradicted facts as a share of all facts in brackets. Each cell has 563 stated facts and 725 facts in total.

| Source | Qwen3 14B | Qwen3.8-27B | gpt-oss-120b |
|---|---|---|---|
| Human transcript | **77.6%** / 69.1% (3.7%) | **89.7%** / 79.9% (5.1%) | **85.3%** / 77.0% (6.5%) |
| Human transcript, normalised | **77.4%** / 68.0% (5.1%) | **90.8%** / 81.0% (5.2%) | **84.9%** / 76.4% (5.5%) |
| Whisper, mixed | **76.2%** / 67.2% (5.2%) | **86.3%** / 77.8% (5.7%) | **82.2%** / 74.8% (6.6%) |
| Qwen3-ASR, mixed | **74.4%** / 67.6% (5.5%) | **88.8%** / 79.7% (5.2%) | **85.6%** / 77.8% (5.7%) |
| Human transcript, judged again (10 consultations) | 78.5% / 65.7% (2.5%) | 94.0% / 78.7% (4.0%) | 86.5% / 74.4% (5.1%) |

The last row covers only 10 consultations and cannot be compared directly with the rows above; it is used only for paired differences.

### 2.4 Heatmap

![Grid heatmap: recall on stated facts](../results/notes/grid/heatmap_stated.svg)

- Each cell is the recall difference against the note written from the human transcript, in percentage points, with its 95% interval; bold means the interval excludes 0.
- The rightmost column is "the same note judged again".
- The regeneration noise, the floor to read every cell against, is noted under the figure.
- Supplementary figure (recall on all facts): `results/notes/grid/heatmap.svg`.
- Tables: `heatmap_stated.csv`, `heatmap.csv`; script: `scripts/plot_grid_heatmap.py`.

### 2.5 Between generation models

Paired by source, bootstrap over consultations (10,000 resamples), recall on stated facts, percentage points.

| Source | 27B − 14B | gpt-oss − 14B | gpt-oss − 27B |
|---|---|---|---|
| Human transcript | +12.1 [+7.8, +16.4] | +7.6 [+4.3, +10.9] | −4.4 [−7.3, −1.4] |
| Human transcript, normalised | +13.3 [+9.8, +17.2] | +7.5 [+4.2, +10.8] | −5.9 [−8.7, −2.9] |
| Whisper, mixed | +10.1 [+6.3, +14.5] | +6.0 [+2.6, +9.7] | −4.1 [−7.1, −1.0] |
| Qwen3-ASR, mixed | +14.4 [+10.0, +18.5] | +11.2 [+7.1, +15.2] | −3.2 [−5.8, −0.4] |

**The generation model matters far more than the ASR, and far more than the noise floor.**

- The 27B is 10–14 points above the 14B, more than five times the noise floor.
- gpt-oss lies between them, 3–6 points below the 27B, with intervals excluding 0 for all four sources.

Recall on all facts gives the same conclusion (27B − 14B: +10.6 to +13.0), see `results/notes/grid/all/paired_summary.csv`. The stated-fact version is `paired_summary_stated.csv`.

### 2.6 Effect of the ASR source

Recall on stated facts against the note written from the human transcript by the same generation model, percentage points.

| Comparison | Qwen3 14B | Qwen3.8-27B | gpt-oss-120b | Three columns pooled |
|---|---|---|---|---|
| Whisper − human | −1.4 [−4.7, +1.8] | −3.4 [−6.3, −0.7] | −3.0 [−5.2, −0.8] | −2.6 [−4.6, −0.7] |
| Qwen3-ASR − human | −3.2 [−6.0, 0.0] | −0.9 [−3.3, +1.5] | +0.4 [−1.9, +2.7] | −1.2 [−2.6, +0.3] |
| Qwen3-ASR − Whisper | −1.8 [−5.0, +1.6] | +2.5 [−0.5, +5.6] | +3.4 [+1.3, +5.3] | +1.4 [−0.3, +3.3] |
| Normalised − human | −0.2 [−2.8, +2.5] | +1.1 [−1.3, +3.5] | −0.4 [−2.6, +2.0] | +0.2 [−1.6, +1.8] |
| *Noise floor: regeneration* | | | | *−0.7 [−3.0, +1.6]* |

"Pooled" puts the facts of all three generation models together, still resampling consultations (25 units).

Conclusions:

- **Whisper, mixed channel: the recall loss is comparable to regeneration noise.**
  - Pooled it is −2.6 points with a paired interval of [−4.6, −0.7], which excludes 0; it also excludes 0 in the 27B and gpt-oss columns separately.
  - But the size of the loss matches the regeneration-noise interval (about ±2 points), so it cannot be taken as a substantive effect.
- **Qwen3-ASR, mixed channel**:
  - Pooled −1.2 [−2.6, +0.3], within the noise floor and indistinguishable from the human transcript.
  - The 14B column alone gives −3.2 with an upper bound of exactly 0, while the other two columns are near 0; the three columns do not agree in direction.
- **Qwen3-ASR vs Whisper**:
  - Pooled +1.4 [−0.3, +3.3], not significant;
  - only the gpt-oss column, +3.4 [+1.3, +5.3], excludes 0, and the 14B column is negative.
  - Conclusion: the WER gap between the two ASR systems (mixed channel, corrected, 8.6% vs 10.3%) does not show up as a stable difference at the note level.
- **Normalised only** (no punctuation, case or fillers): +0.2 [−1.6, +1.8], almost no effect on the notes.

**Supplementary: recall on all facts**

| Comparison (pooled) | Difference in recall on all facts |
|---|---|
| Whisper − human | −2.1 [−4.1, −0.1] |
| Qwen3-ASR − human | −0.3 [−2.1, +1.7] |
| Qwen3-ASR − Whisper | +1.8 [−0.1, +3.8] |
| *Noise floor: regeneration* | *0.0 [−1.9, +1.9]* |

Same conclusion as the primary metric.

### 2.7 Contradicted facts

On stated facts, notes from ASR sources contain slightly more contradicted facts than notes from the human transcript (pooled, percentage points):

| Comparison | Difference in the share of contradicted facts |
|---|---|
| Whisper − human | +1.5 [+0.7, +2.3] |
| Qwen3-ASR − human | +1.2 [+0.5, +2.0] |
| Normalised − human | +0.5 [−0.1, +1.1] |

- Both ASR systems are significant, but the effect is only 1–2 points.
- On all facts, neither is significant (Whisper +0.7 [−0.2, +1.7], Qwen3-ASR +0.4 [−0.5, +1.2]).
- Contradicted facts are the most direct note-level risk; see the key cases in 2.10, e.g. the "not → also" meaning flip.

### 2.8 Why facts are missing from notes

This section must use **all facts** as the denominator, because "never said in the conversation" is itself one of the categories. Each cell has 725 facts.

| Source | Generation model | Not in note | Never said | Partly said | Generator's own omission (missing from both notes) | **Lost only because of this source** |
|---|---|---|---|---|---|---|
| Normalised | 14B / 27B / gpt-oss | 32.0 / 19.0 / 23.6% | 5.7 / 5.7 / 5.0% | 6.6 / 4.3 / 5.0% | 12.1 / 4.3 / 7.0% | **4.7 / 2.2 / 4.0%** |
| Whisper, mixed | 14B / 27B / gpt-oss | 32.8 / 22.2 / 25.2% | 5.8 / 5.4 / 5.0% | 6.8 / 4.3 / 4.7% | 11.2 / 5.0 / 7.4% | **6.8 / 5.0 / 5.8%** |
| Qwen3-ASR, mixed | 14B / 27B / gpt-oss | 32.4 / 20.3 / 22.2% | 5.5 / 5.5 / 4.8% | 5.7 / 4.7 / 4.6% | 13.4 / 5.0 / 7.3% | **5.9 / 3.2 / 3.3%** |

- **Share of facts lost only because of the source** (present in the human-transcript note, missing here):
  - The "normalised only" control already has 2.2–4.7%. This too is regeneration noise: a slightly different input makes greedy decoding write a different note.
  - Qwen3-ASR has 3.2–5.9%, Whisper 5.0–6.8%.
  - Both ASR systems are only 1–2 points above that control.
- **Most facts missing from notes are not caused by the transcript.** They come mainly from three places:
  - never said in the conversation (about 5–6%);
  - only partly said (about 4–7%);
  - the generation model's own omissions (14B about 11–13%, 27B about 4–5%).

  So a better generation model gains more than a better ASR system.

### 2.9 What notes add

Negative findings ("no ...", not necessarily asked about) added per note on average:

| Generation model | Added negative findings per note |
|---|---|
| Qwen3 14B | 2.4–2.8 |
| Qwen3.8-27B | 2.6–3.1 |
| gpt-oss-120b | 3.1–3.5 |

Within a generation model, the sources barely differ: these added negatives are determined by the generation model, not by the transcript source. Clinically dangerous examples are in 2.10.

### 2.10 Key cases

See `results/notes/grid/key_cases.md`; each case has the consultation id, time, original text and a viewer link:

- negation flips: the ASR dropped a negation;
- meaning flips: not ↔ also;
- negative findings invented by the generation model, e.g. "no neck stiffness" in a headache-with-photophobia consultation.

## 3. Limitations

- **Small sample**: 25 consultations per cell. Differences between ASR systems lie near the noise floor.
- **The noise floor comes from one cell**: regeneration noise was measured only for the 14B on the human transcript (local vs A100). Other cells were not measured separately; this document assumes their regeneration noise is of similar size.
- **Mixed channel only**: Qwen3-ASR has no word timestamps, so the separated-channel comparison was not done.
- **The generation models are a set of representatives, not a size ladder**: they differ in family, generation, architecture and quantisation format (Q4_K_M vs MXFP4), and gpt-oss runs with low-effort reasoning.
- **One generation per cell**: greedy decoding, fixed seed.
- **Judge vs generators**: the judge is Claude (Opus 5.5). No grid notes were written by Claude, so there is no same-family self-preference bias.
- **Dataset**: PriMock57 simulated telehealth consultations; reference notes written by one clinician.

## 4. Files

| Contents | Location |
|---|---|
| Judgements per column | `results/notes/grid/<model>/`: `scores.csv`, `fact_labels.csv`, `summary.csv`, `paired_summary.csv`, `discordant_facts.csv`, `spotcheck.csv` |
| Missing-fact attribution and additions per column | `results/notes/grid/<model>/error_composition/` |
| Grid summary (both recalls) | `results/notes/grid/grid_summary.csv`, `grid.md` |
| Paired comparisons: stated facts (primary) | `results/notes/grid/all/paired_summary_stated.csv` |
| Paired comparisons: all facts (supplementary) | `results/notes/grid/all/paired_summary.csv` |
| Regeneration noise | `results/notes/grid/regeneration_noise.csv` |
| Heatmaps | `results/notes/grid/heatmap_stated.svg` (primary), `heatmap.svg` (supplementary) |
| Key cases | `results/notes/grid/key_cases.md` |
| Note texts | `outputs/notes-grid/notes/<model>/` (not committed) |
| Scripts | `scripts/run_grid.sh`, `scripts/generate_notes.py`, `scripts/combine_grid.py`, `scripts/compare_notes.py` (new `--stated`), `scripts/recall_definitions.py`, `scripts/plot_grid_heatmap.py` |
