# Choosing the "best 2026 ASR": Qwen3-ASR-1.7B

47 test consultations, comparison mainly on the mixed channel. All intervals are paired bootstrap: consultations resampled with replacement 10,000 times, the same resamples for every model, 95% interval. Script: `scripts/bootstrap_asr.py`; all pairwise comparisons in `bootstrap/pairwise.csv`.

## 1. Three metrics (mixed channel)

| Run | Corrected WER | Medical-term error rate | Clinical-negation loss |
|---|---|---|---|
| **Qwen3-ASR-1.7B** | **8.62%** | **5.57%** | **2.2%** |
| Canary-Qwen 2.5B | 9.67% | 6.24% | 3.6% |
| Parakeet (shared chunk plan) | 9.96% | 6.47% | 5.0% |
| Whisper large-v3 (built-in VAD, original main result) | 10.29% | 6.83% | 5.0% |
| Parakeet (whole files) | 10.66% | 6.31% | 6.8% |
| Whisper large-v3 (shared chunk plan) | 10.78% | 6.62% | 7.0% |
| Cohere Transcribe | 11.47% | 6.21% | 8.2% |
| Granite Speech 4.1 2B | 12.60% | 7.79% | 8.6% |

Reference counts (denominators): 68,050 reference words, 9,837 medical-term words, 500 clinical negations.

- Medical-term error rate = share of medical-term words substituted or deleted.
- Clinical-negation loss = share of clinical negations deleted or replaced by a non-negation.

## 2. Qwen3-ASR against every other model (percentage points, Qwen3-ASR minus the other, 95% interval)

| Comparison | Corrected WER | Medical-term error rate | Clinical-negation loss |
|---|---|---|---|
| vs Canary-Qwen 2.5B | −1.06 [−1.31, −0.80] | −0.67 [−1.06, −0.27] | −1.40 [−2.80, −0.20] |
| vs Whisper (built-in VAD) | −1.67 [−2.09, −1.27] | −1.26 [−1.76, −0.78] | −2.80 [−4.55, −1.11] |
| vs Whisper (shared chunk plan) | −2.16 [−2.52, −1.81] | −1.05 [−1.50, −0.59] | −4.80 [−7.03, −2.79] |
| vs Parakeet (shared chunk plan) | −1.35 [−1.69, −1.00] | −0.89 [−1.32, −0.49] | −2.80 [−5.01, −1.01] |
| vs Parakeet (whole files) | −2.04 [−2.47, −1.63] | −0.74 [−1.16, −0.32] | −4.60 [−6.71, −2.58] |
| vs Cohere Transcribe | −2.85 [−3.51, −2.26] | −0.64 [−1.06, −0.23] | −6.00 [−8.76, −3.51] |
| vs Granite Speech 4.1 2B | −3.98 [−4.49, −3.49] | −2.22 [−2.66, −1.77] | −6.40 [−8.78, −4.12] |

Against every model and on every metric, Qwen3-ASR's interval excludes 0. The closest is negation loss against Canary: the upper bound is only −0.20, because there are only 500 clinical negations, so the evidence there is weaker.

Many differences between the other models include 0. For example:
- Whisper (built-in VAD) vs Parakeet (shared chunk plan): WER +0.33 [−0.09, +0.77].
- On medical-term error rate, Canary, Parakeet, Whisper and Cohere are mostly indistinguishable.

So the ranking of the middle models is not stable. External reports say only "Qwen3-ASR is best; the others are close within the error margin" and do not rank places 2–5.

## 3. Long repetitions (the same word ≥ 10 times in a row)

Script: `scripts/count_repeats.py`, results in `repeats/`. "Phrase loops" in the table are a 2–4 word unit repeated ≥ 5 times in a row. The reference transcripts contain none of either, so all of these are model hallucinations.

| Run | Channel | Same-word runs: count (words) | Phrase loops: count (words) | Consultations affected |
|---|---|---|---|---|
| Qwen3-ASR-1.7B | all | 0 | 0 | 0 |
| Whisper (shared chunk plan) | all | 0 | 0 | 0 |
| Parakeet (shared chunk plan) | all | 0 | 0 | 0 |
| Canary-Qwen 2.5B | patient | 1 (23) | 0 | 1 |
| Whisper (built-in VAD) | mixed | 0 | 1 (10, "thank you" × 5) | 1 |
| Parakeet (whole files) | patient | 1 (138, "no") | 0 | 1 |
| Cohere Transcribe | mixed | 1 (185, "next") | 0 | 1 |
| Granite Speech 4.1 2B | patient | 7 (1,500) | 1 (367) | 7 |

The location of each (consultation, channel, start and end time, segments involved) is in `repeats/repeats.csv`.

Granite's repetitions are about 200 words each: a 30 s chunk generated up to the 400-token limit and was cut off. With a higher limit the repetitions would only get longer.

## 4. Choice and reasons

As planned, **Qwen3-ASR-1.7B** (`Qwen/Qwen3-ASR-1.7B`) is the "best 2026 ASR" for the note-level grid:

1. **Lowest WER on all three tracks**: doctor 6.1%, patient 9.5%, mixed 8.6% (corrected). On the mixed channel it is 1.06 points below the runner-up Canary and 1.67 points below the Whisper main result, both intervals excluding 0.
2. **Best on the two metrics that matter most for notes**:
   - medical-term error rate 1.26 points below Whisper;
   - clinical-negation loss less than half of Whisper's (2.2% vs 5.0%).
3. **No long repetitions**: none in 47 consultations × 3 tracks.
4. **Runs locally, permissive licence**: Apache 2.0, 1.7B parameters, runs on the 16 GB 5080, about as fast as Whisper large-v3 (mixed channel about 5.5 s per audio minute).

**Caveats:**

- **Overlap is not solved.** Qwen3-ASR still deletes 20.3% of the words inside overlaps on the mixed channel (7.1% on the separated channels). The speaker who comes in loses 19.6 points more, as with every other model. A different model does not fix this.
- **One dataset.** The results come from 47 simulated PriMock57 consultations (British accents, telehealth) and do not represent other accents or real clinical recordings.
- **Chunking may favour some models.** Qwen3-ASR uses the shared chunk plan (`plan_chunks.py`, ≤ 30 s, cut at pauses). A different segmentation could shift the ranking slightly: Whisper's own VAD segmentation is 0.5 points better for it than the shared plan.
- **Separated-channel notes need word timestamps, which Qwen3-ASR does not output.** Separated-channel notes interleave the two channels into turns using word timestamps, but Qwen3-ASR outputs only segment text by default. Two options:
  - add word times with the official forced-alignment model (Qwen3-ForcedAligner, to be verified);
  - fall back to interleaving by chunk (≤ 30 s), which is coarser and makes the separated-channel row not fully comparable with Whisper's.

  **Decided (2026-10-27)**: the note grid uses the mixed channel only; the separated-channel comparison is not done and is stated as a limitation.
