# Stress test: does the bottleneck move from "writing" to "listening" as conditions get worse?

Branch: `stress-test`. Started 2026-10-27.

The current main conclusion — the bottleneck is in writing the note, not in listening — comes from PriMock57: two people, a quiet room, video-call audio. The target setting (a trauma bay) has more people, more noise, far-field microphones and more interruptions. The stress test asks two questions:

1. **ASR level**: as conditions get worse, how does each kind of error grow? Are deletions in overlaps still concentrated on the speaker who comes in?
2. **Note level**: how bad must conditions get before the ASR's effect exceeds the generation model's?

**What the stress test is for**: not to reproduce a real setting, but to raise the pressure step by step and watch how errors grow. Like stress-testing a circuit beyond its rated voltage, 2× and 3× overlap and 0 dB SNR are meant to be worse than everyday conversation. Only each factor's 1× or no-noise level represents the real level.

## 1. Fixed rules

- **What is committed**: one commit per completed step. Synthesised audio, noise material and listening clips are not committed; only scripts, configs (`configs/stress/*.yaml`) and result tables.
- **Reproducible**: every synthesis uses a fixed random seed, with parameters in the configs, reproducible with one command.
- **Dev set first, then test set**: synthesis is validated on the dev set (first 10 consultations, `data/prepared_full10`) before running the test set.
- **The normaliser and judge protocol v1 are frozen.**
- **GPU and rental** (revised 2026-10-27; the original plan was "no rented GPUs"):
  - The ASR part (synthesised audio, Qwen3-ASR and Whisper) runs on the local RTX 5080, one GPU job at a time.
  - The note level runs on one rented RunPod A100 80GB, in the same environment as the stage-3 grid: Ollama 0.40.11, Qwen3.8-27B Q4_K_M, same settings.
  - Within **the same rental session**, the human-transcript column is regenerated first and then the stress-condition notes, so their difference is free of regeneration noise.
  - Budget cap **$10**. The estimated time and cost are sent to the project lead for approval before starting the machine; the pod is stopped and deleted as soon as the run finishes.
- **Where a trade-off is needed**, stop and ask.

## 2. Expected results (written before running; each checked afterwards)

1. **S1 more overlap**: the deletion rate rises roughly linearly with the overlap ratio, mainly for the speaker who comes in. The gap between Qwen3-ASR and Whisper does not change much as overlap grows, because both have the same source of trouble.
2. **S2 a third speaker**: insertions increase, and a fair share of them match the third speaker's words. Whisper writes in background speech more readily than Qwen3-ASR.
3. **S3 background noise**: WER rises sharply at 0–5 dB, and Whisper's long repetitions and hallucinations increase clearly. Qwen3-ASR's advantage widens at low SNR.
4. **S4 reverberation / far field**: overall WER rises; the speaker farther from the microphone is hit harder.
5. **Note level**: at 3× overlap and low SNR, the recall loss caused by the ASR becomes significantly negative. At least for Whisper it approaches or exceeds 5 percentage points — the bottleneck starts to move from writing to listening.

If prediction 5 does not hold — if the ASR's effect stays small even under extreme conditions — that is a strong conclusion in itself and will be reported as such.

## 3. Related work

- **Denoising hurts**: Chondhekar et al. (arXiv 2512.17562, December 2025, "When De-noising Hurts").
  - Method: MetricGAN+ denoising before Whisper, Parakeet, Gemini Flash 2.0 and Parrotlet-a.
  - Result: in all 40 configurations, medical ASR on denoised audio was worse than on the original noisy audio, by 1.1–46.6 points of absolute semWER.
  - So this project **does not consider "denoise first, then recognise"**; stress conditions go straight into the ASR.
- **WER barely changes while clinical meaning flips**: Jiang et al. (arXiv 2606.05909, INTERSPEECH 2026, "Beyond WER: A Paired Acoustic Stress Test for Ambient Clinical Scribes").
  - Method: several kinds of noise added to the same dialogues, with the downstream model kept fixed.
  - Result: stationary ambient noise raised WER by only 0.71 points but nearly doubled the rate of unsafe outputs; small acoustic perturbations can invert clinical meaning.
  - This agrees with stage 3 of this project: on stated facts, the ASR mainly adds contradicted facts rather than omissions; "drinking little" written as "drinking a lot" is one example.
- **Speech is the main source of ICU noise**: a University of Portsmouth soundscape study of three ICUs in Iraq found that over 50% of the cumulative acoustic noise came from conversation (staff and visitors).
  - Paper: *Acoustics Australia*, 2024, DOI 10.1007/s40857-024-00321-3.
  - Press release: https://www.port.ac.uk/news-events-and-blogs/news/study-finds-staff-and-visitor-voices-are-major-source-of-excessive-noise-in-hospital-icus
  - This is why the main S3 condition uses a speech-babble background.

## 4. Method

### Common to all factors

- Each stress factor is swept **on its own**, with everything else at baseline (mixed channel).
- Synthesised data use the same format as `prep_data.py`: `mixed.wav` plus `utterances.json` and `ref_*.txt`, so `transcribe.py`, `evaluate.py` and the other scripts run unchanged.
- The mixed channel is made as in the baseline: summed, then peak-normalised to −1 dBFS.
- Both ASR systems use their stage-2 settings:
  - Whisper large-v3: `--vad --no-condition-on-previous-text`
  - Qwen3-ASR-1.7B: the shared chunk plan, re-planned **on each condition's own audio** (`plan_chunks.py`).
- Run script: `scripts/run_stress_asr.ps1`.

### S1 more overlap (`scripts/stress_overlap.py`, `configs/stress/s1_overlap.yaml`)

**Synthesis**:

- **Cut**: each utterance is cut from its speaker's clean channel, with 0.15 s padding at each end that never reaches into the same speaker's neighbouring utterance.
- **Re-place**: the cut utterances are placed on a new time line. At a share p of the turn changes, the next speaker starts d seconds early, into the previous speaker's utterance. Everything after it moves earlier by the same amount, so the rest of the conversation keeps its own timing.
- **Two limits**:
  - the next speaker never starts before the previous utterance has run 0.4 s;
  - a speaker's utterances never overlap each other.
- **Level 1× is re-synthesised too**, with the same cut-and-place method and d = 0 (original timing). Every level then shares the synthesis artefacts and differs only in the amount of overlap.
- **Reference**: reordered by the new start times; each utterance's word times move with its shift.

**Overlap ratio**: seconds where both speakers talk ÷ seconds where anyone talks, from utterance intervals.

**Calibration** (dev set, 10 consultations): baseline overlap ratio 0.0751.

| Level | d (s) | Dev-set overlap ratio | vs baseline | Turn changes started early |
|---|---|---|---|---|
| s1_1x | 0 | 0.0751 | 1.00× | 0 / 972 |
| s1_2x | 0.86 | 0.1502 | 2.00× | 864 / 972 |
| s1_3x | 1.65 | 0.2255 | 3.00× | 805 / 972 |

The larger d is, the more turn changes the two limits stop from starting early, so fewer turn changes are shifted at 3× than at 2×.

**d recalibrated on the test set** (`configs/stress/s1_overlap_test47.yaml`):

- The test set has less overlap than the dev set: baseline ratio 0.0479 vs 0.0751.
- With the dev-set d values, the test set would reach 2.75× and 4.46× of its own baseline, beyond the targets.
- So d was recalibrated on the test set with the same method; all other parameters are unchanged.
- The calibration uses only utterance times and no ASR output, so nothing about test-set results leaks into it.

| Level | d (s) | Test-set overlap ratio | vs test-set baseline | Turn changes started early |
|---|---|---|---|---|
| s1_1x | 0 | 0.0479 | 1.00× | 0 / 4318 |
| s1_2x | 0.55 | 0.0961 | 2.01× | 3971 / 4318 |
| s1_3x | 0.97 | 0.1442 | 3.01× | 3859 / 4318 |

**Why p = 1.0**:

- with p = 0.6, reaching 3× needs a 2.75 s head start, far longer than real interruptions (typically 0.5–1.5 s of overlap);
- with p = 1.0, 2× and 3× need only 0.86 s and 1.65 s.
- p = 1.0 is the lesser of the two problems.

**Limitation of p = 1.0**: in real conversation only some turn changes overlap; p = 1.0 means every change of speaker is an interruption, which is more extreme than reality.

**Compared with real conversation** (dev set, 10 consultations, 972 turn changes). Level 1× uses PriMock57's original timing and serves as the real-conversation reference.

| Level | Turn changes with overlap | Overlap length at those turn changes: median | 90th percentile |
|---|---|---|---|
| **1× (PriMock57 original timing, real reference)** | **50%** | **0.74 s** | **5.7 s** |
| 2× | 75% | 0.92 s | 4.9 s |
| 3× | 84% | 1.35 s | 5.3 s |

- **The original conversations already overlap a lot**: half the turn changes overlap, some for over ten seconds. Most of these are one person saying "yeah", "mm" or "okay" while the other is talking; each backchannel is its own utterance in the annotation, so it counts as a turn change.
- **What the stress adds**: at 3× the typical overlap grows from 0.74 s to 1.35 s, and turn changes with overlap go from 50% to 84%. The 90th percentile does not grow, so the synthesis does not create unnaturally long stretches of both people talking.
- The statistics come from a one-off check; the numbers are recorded here.

**Listening check** (2026-10-27, project lead, not a native English speaker):

- Three dev consultations drawn with a fixed seed; in each, the 30 s with the most overlap at 3×, and the same stretch of conversation at 1× and 2×. Files in `results/stress/listen/s1/`, not committed.
- Verdict: the 3× level is "a bit crowded but still a normal conversation", not two recordings mechanically laid on top of each other. **Passed.**
- Not checked by a native English speaker.

**1× vs the original mixed channel** (dev set, Whisper large-v3):

| | WER | Substitutions | Deletions | Insertions | Deletion rate in overlap | Deletion rate outside overlap |
|---|---|---|---|---|---|---|
| Original mixed channel | 17.15% | 995 | 1534 | 401 | 27.1% | 6.7% |
| S1 1× (re-synthesised) | 16.57% | 1014 | 1419 | 399 | 26.8% | 6.0% |

- WER is 0.6 points lower after re-synthesis, mainly from fewer deletions outside overlap: the gaps between utterances are pure silence in the synthesis, so the original channels' background noise and crosstalk are gone.
- This is an artefact of the synthesis method, which is why 2× and 3× are compared only with 1×, never with the original mixed channel.
- The deletion rate inside overlap is almost the same.

### S2 a third speaker

Not run (dropped for time; see section 6).

### S3 background noise (`scripts/stress_noise.py`, `configs/stress/s3_noise.yaml`)

**Noise**: two environments from DEMAND (Thiemann et al., 2013; Zenodo record 1227121), 16 kHz versions:

- **PCAFETER**: cafeteria
- **PRESTO**: restaurant

Both are dominated by speech babble, with tableware and footsteps.

**Why a speech background**: the ICU soundscape study found that over 50% of the cumulative noise came from conversation (section 3).

**Licence**:

- The Zenodo record lists CC BY 4.0; the PDF shipped with the data lists CC BY-SA 3.0.
- Used for research, mixed only into locally synthesised audio; no audio is redistributed.

**Why not MUSAN**: the full corpus is 11 GB and has no ready-made babble; it would have to be built from its speech part.

**Why not m42-health/hospital_ambient_noise** (Hugging Face):

- the dataset card shows only the field structure, with no licence and no description of the recordings;
- the content is speech recorded with hospital noise (with transcripts), not pure background noise.
- With an unclear licence, it is not used.

**Synthesis**:

- Noise is added to the **original mixed channel** and the reference is unchanged, so the S3 no-noise baseline is the existing stage-2 result and needs no re-synthesis.
- For each consultation, with a fixed seed:
  1. one of the two environments is chosen;
  2. its 16 channels (one microphone array, about 5 minutes each) are joined in random order;
  3. a stretch as long as the consultation is cut from a random offset.

  So even a ten-minute consultation never hears the same noise twice.
- **SNR** = speech power ÷ noise power, with speech power measured only inside utterance intervals.
- After mixing, the audio is peak-normalised to −1 dBFS.

**Levels**: 20, 10, 5 and 0 dB. On the dev set, every consultation's achieved SNR is within ±0.1 dB of the target; each consultation's environment and achieved SNR are recorded in `data/stress/<set>/s3_levels.json`.

**Limitation**: neither environment contains **medical equipment sounds** (monitors, infusion pumps, ventilators); S3b covers this only in part.

### S3b speech background plus alarms (same script and config, level `s3b_snr10_alarms`)

**Method**:

- Alarm sounds are added at random on top of S3's 10 dB speech background.
- The background is identical to `s3_snr10` — same environment, same stretch of noise; the files were checked to be byte-for-byte identical — so the two levels differ **only by the alarms**.

**Parameters**:

- **Rate**: the number of alarms per minute is a random integer from 2 to 4 (fixed seed).
- **Length**: each alarm is a 3–6 s excerpt with 20 ms fade-in and fade-out.
- **Loudness**: each alarm's power equals the speech power (0 dB relative to speech). This is provisional, set in the config, and can be changed.
- **Record**: each consultation's alarm times are recorded in `s3_levels.json`.

**Material**: Freesound, **all CC0 1.0** (checked on each sound's page on 2026-10-27). Originals require a login, so the public high-quality previews are used (MP3, resampled to 16 kHz).

| File | Title and author | Link | Licence |
|---|---|---|---|
| 668978 | "beeps for heart monitor.wav", vestibule-door | https://freesound.org/people/vestibule-door/sounds/668978/ | CC0 1.0 |
| 148897 | "Heart Monitor Beep", samfk360 | https://freesound.org/people/samfk360/sounds/148897/ | CC0 1.0 |
| 617170 | "Hospital infusion pump. Alarm", SonoRec | https://freesound.org/people/SonoRec/sounds/617170/ | CC0 1.0 |

Two other CC0 candidates were not used:

- 617280: the infusion pump's motor running, not an alarm;
- 832259: "beeps02", with no description of what it is.

**Limitations**:

- only 3 alarm recordings, all from the internet; they do not represent any particular hospital's equipment;
- the alarm loudness is provisional;
- equipment sounds other than alarms (ventilators, suction, etc.) are not covered.

### S4 reverberation / far field

Not run (dropped for time; see section 6).

## 5. Results

**Data**: test set, 47 consultations, mixed channel, 68,168 reference words per level. Summary table: `results/stress/test47/asr_summary.csv`; per-level analysis in `results/stress/test47/<level>/`. Intervals are 95% bootstrap intervals over consultations (10,000 resamples). Dev-set (10 consultations) results are in `results/stress/full10/` and were used only to validate the synthesis.

**Achieved SNR on the test set**: within ±0.4 dB of the target for every consultation (six consultations are off by 0.1–0.37 dB, the same offset at every level); 23 consultations use PCAFETER and 24 PRESTO. S3b adds 1,278 alarm events in total.

### 5.1 ASR level

**Corrected WER** (raw WER in `asr_summary.csv`):

| Level | Whisper large-v3 | Qwen3-ASR-1.7B | Qwen3-ASR − Whisper |
|---|---|---|---|
| S1 1× | 10.0% [9.3, 10.7] | 8.4% [7.8, 9.0] | −1.65 [−1.96, −1.37] |
| S1 2× | 11.2% [10.3, 12.0] | 9.3% [8.7, 10.0] | −1.86 [−2.28, −1.47] |
| S1 3× | 13.3% [12.4, 14.2] | 11.1% [10.4, 11.9] | −2.12 [−2.47, −1.76] |
| S3 no noise (stage 2) | 10.3% [9.5, 11.1] | 8.6% [8.1, 9.2] | −1.67 [−2.09, −1.27] |
| S3 20 dB | 12.3% [11.5, 13.1] | 9.9% [9.2, 10.6] | −2.41 [−2.90, −1.94] |
| S3 10 dB | 15.5% [14.4, 16.5] | 13.3% [12.3, 14.3] | −2.14 [−2.58, −1.69] |
| S3 5 dB | 20.3% [19.0, 21.6] | 18.8% [17.2, 20.2] | −1.53 [−2.13, −0.94] |
| S3 0 dB | 31.4% [29.2, 33.6] | 32.8% [30.2, 35.3] | **+1.37 [+0.48, +2.31]** |
| S3b 10 dB + alarms | 16.0% [14.9, 17.1] | 13.8% [12.7, 14.8] | −2.29 [−2.76, −1.78] |

Figures: `results/stress/test47/fig_s1_overlap.svg`, `fig_s3_noise.svg`, `fig_overlap_came_in.svg`.

**Test-set 1× vs the original mixed channel**: Whisper 10.0% vs 10.3%, Qwen3-ASR 8.4% vs 8.6%. As on the dev set, re-synthesis lowers WER slightly (fewer deletions outside overlap, 3.9% vs 4.1% for Whisper); the deletion rate inside overlap is the same (25.3% vs 25.3%). S1 levels are therefore compared only with S1 1×.

**Error composition** (rate per reference word):

| Level | Model | Substitutions | Deletions | Insertions | Deletions outside overlap | Deletions inside overlap | … speaker who came in | … speaker holding the turn |
|---|---|---|---|---|---|---|---|---|
| S1 1× | Whisper | 5.0% | 5.5% | 1.8% | 3.9% | 25.3% | 34.6% | 17.4% |
| S1 1× | Qwen3-ASR | 5.0% | 4.0% | 1.8% | 2.7% | 20.1% | 29.0% | 12.5% |
| S1 2× | Whisper | 4.9% | 6.7% | 1.7% | 4.0% | 21.5% | 27.4% | 16.2% |
| S1 2× | Qwen3-ASR | 5.0% | 4.8% | 1.7% | 2.8% | 16.2% | 21.3% | 11.6% |
| S1 3× | Whisper | 4.6% | 9.0% | 1.4% | 4.3% | 24.5% | 30.6% | 19.1% |
| S1 3× | Qwen3-ASR | 4.7% | 7.0% | 1.4% | 3.1% | 19.9% | 23.4% | 16.8% |
| S3 no noise | Whisper | 5.0% | 5.7% | 1.9% | 4.1% | 25.3% | 34.4% | 17.5% |
| S3 no noise | Qwen3-ASR | 5.0% | 4.1% | 1.9% | 2.9% | 20.3% | 29.1% | 12.9% |
| S3 10 dB | Whisper | 5.7% | 9.8% | 1.6% | 8.2% | 30.8% | 37.8% | 24.8% |
| S3 10 dB | Qwen3-ASR | 6.5% | 7.2% | 1.6% | 5.7% | 25.9% | 32.4% | 20.4% |
| S3 5 dB | Whisper | 7.0% | 12.7% | 2.0% | 10.9% | 34.3% | 41.0% | 28.6% |
| S3 5 dB | Qwen3-ASR | 7.9% | 11.0% | 1.5% | 9.5% | 30.4% | 36.0% | 25.7% |
| S3 0 dB | Whisper | 11.4% | 18.6% | 2.3% | 16.9% | 39.6% | 45.4% | 34.6% |
| S3 0 dB | Qwen3-ASR | 10.9% | 21.8% | 1.2% | 20.0% | 44.5% | 49.6% | 40.2% |

**Medical terms and clinical negations** (500 clinical negations in the reference; "lost" = deleted or replaced by a non-negation):

| Level | Medical-term error rate, Whisper | Qwen3-ASR | Clinical negations lost, Whisper | Qwen3-ASR |
|---|---|---|---|---|
| S1 1× | 6.5% | 5.4% | 5.2% [3.6, 6.9] | 2.4% [1.3, 3.6] |
| S1 3× | 10.0% | 8.1% | 8.2% [5.6, 10.9] | 5.4% [3.6, 7.3] |
| S3 no noise | 6.8% | 5.6% | 5.0% [2.9, 7.1] | 2.2% [1.1, 3.4] |
| S3 10 dB | 11.2% | 10.5% | 9.8% [7.4, 12.3] | 6.6% [4.4, 9.1] |
| S3 5 dB | 16.4% | 16.3% | 16.6% [13.2, 20.2] | 11.0% [8.7, 13.4] |
| S3 0 dB | 28.7% | 32.7% | 26.0% [21.3, 30.8] | 25.0% [21.1, 29.1] |
| S3b 10 dB + alarms | 12.0% | 11.0% | 11.2% [8.1, 14.3] | 7.0% [5.0, 9.1] |

**Long repetitions**: rare at every level — at most 3 phrase loops and 2 same-word loops per model and level (Whisper at 0 dB and 5 dB); none for Qwen3-ASR.

### 5.2 Predictions checked

1. **S1 — partly holds.**
   - Total deletions rise with overlap (Whisper 5.5% → 6.7% → 9.0%), but the deletion rate *per word inside overlap* does not rise (Whisper 25.3% → 21.5% → 24.5%). The growth comes from more words falling inside overlap, not from each overlapped word being harder.
   - The speaker who came in is deleted about twice as often as the one holding the turn at every level, but the growth is **not** concentrated on them: their deletion rate is flat or lower at 2× and 3× (Whisper 34.6% → 27.4% → 30.6%). On the dev set the rise was in the holding role; on the test set neither role rises clearly. Not as predicted.
   - WER rises faster than linearly: +1.2 points from 1× to 2×, +2.1 from 2× to 3× (Whisper).
   - The Qwen3-ASR advantage stays about the same, widening slightly (−1.65 → −2.12 points, overlapping intervals). Holds.
   - Overall, tripling overlap raises corrected WER by only 3 points (Whisper 10.0% → 13.3%); overlap is a mild stressor compared with noise.
2. **S2 — not run** (dropped for time; see section 6).
3. **S3 — partly holds, and one part is reversed.**
   - WER rises sharply at 0–5 dB: holds (Whisper 10.3% → 20.3% at 5 dB → 31.4% at 0 dB).
   - Whisper's long repetitions increase clearly: **does not hold** — at most 3 loops at any level. With VAD and no conditioning on previous text, the stage-2 Whisper setting is robust to this failure even in noise.
   - Qwen3-ASR's advantage widens at low SNR: **reversed**. The advantage is largest at 20 dB (−2.4 points), shrinks at 5 dB (−1.5), and at 0 dB Qwen3-ASR is worse than Whisper (+1.4 [+0.5, +2.3]). Qwen3-ASR fails by dropping speech: at 0 dB its deletion rate is 21.8% vs Whisper's 18.6%, with fewer insertions (1.2% vs 2.3%). On medical terms the advantage is already gone at 5 dB (16.3% vs 16.4%).
   - Clinical negations: Qwen3-ASR loses fewer than Whisper down to 5 dB (11.0% vs 16.6%); at 0 dB both lose about a quarter.
   - **S3b alarms** add little on top of the 10 dB background: +0.6 points for Whisper, +0.4 for Qwen3-ASR (no interval computed for this difference). At 0 dB relative to speech and 2–4 alarms per minute, the alarms are a much weaker stressor than lowering the babble SNR by 5 dB.
4. **S4 — not run** (dropped for time; see section 6).
5. **Note level — holds.** The recall loss is −5.9 points at 5 dB for both models and about −14 points at 0 dB, the same size as the 27B − 14B generation-model gap (+12.1). Details in section 5.4.

### 5.3 Key cases

Times are the start of the utterance in the original PriMock57 timing. Each case is a clinical negation that the model kept at the baseline level and lost at the stressed level.

| # | Consultation · time | Level | Original (human transcript) | ASR output at the stressed level |
|---|---|---|---|---|
| S1-a | day2_consultation08 · 482.8 s, patient | S1 3× | "Mmm, moderate alcohol intake. Yeah, I **don't** drink too much." | Both models drop the negation with its clause; at 1× both keep "I do not drink too much". The alcohol history answer disappears. |
| S1-b | day1_consultation14 · 593.8 s, patient | S1 3× | "OK. But otherwise, I **don't** need to worry." | Both models drop it at 3×; both keep it at 1×. |
| S3-a | day1_consultation15 · 112.7 s, patient | S3 5 dB | "…yes it has bled sometimes but, yeah. Otherwise, it **hasn't bled** on its own." | Qwen3-ASR: "otherwise it has **blood** okay okay" — the negation becomes a positive. Correct with no noise. |
| S3-b | day1_consultation12 · 436.7 s, doctor | S3 5 dB | "And if you're still **not** better next week, I want you to come back" | Qwen3-ASR: "if you feel a **lot** better next week" — the safety-net advice is inverted. |
| S3-c | day1_consultation13 · 186.5 s and 193.2 s | S3 5 dB | Patient: "But I, **no vomiting**." Doctor restates: "Yeah, **no vomiting**, OK." | Whisper drops "no" both times. In the clean audio the doctor's restatement protects such answers (stage-3 case A2); in noise both copies are lost together. |
| S3b-a | day2_consultation04 · 542.5 s, doctor | S3b | "…a follow-up chest X-ray, if things **don't** settle down." | Qwen3-ASR: "x ray things going **from** session down". Correct at 10 dB without alarms. |

Counts of clinical negations kept at the baseline level and lost at the stressed level (same model, same context): S1 3× Whisper 16, Qwen3-ASR 12; S3 5 dB Whisper 55, Qwen3-ASR 39; S3b (vs S3 10 dB) Whisper 14, Qwen3-ASR 5.

### 5.4 Note level

**Conditions: S3 5 dB and S3 0 dB** (decided 2026-10-28 after the ASR results; the plan named S1 3× and one S3 level).

- **Why S1 3× is not run**: it raises corrected WER by only about 3 points (Whisper 10.0% → 13.3%, Qwen3-ASR 8.4% → 11.1%), a factor of about 1.3. In stage 3 a 1.7-point WER gap between the two ASR systems already gave note-level differences within the ±2-point regeneration noise. An increment of this size is not expected to produce a measurable note-level effect, so renting a GPU for it is not worth it.
- **Why 5 dB and 0 dB**:
  - Same factor at two strengths, about 2× and 3× baseline WER, gives a dose-response curve: the level at which the bottleneck moves from writing to listening, if it does, is visible.
  - 0 dB is where Qwen3-ASR falls behind Whisper, and the two fail differently: Qwen3-ASR drops whole stretches (deletions 21.8% vs 18.6%), Whisper mishears more (more substitutions and insertions). Deletions should show up as missing facts and substitutions as contradicted facts; the note level can test this correspondence directly.
  - About a quarter of clinical negations are lost at 0 dB, so negation flips reaching the notes are likely.

**Setup**: Qwen3.8-27B (`qwen3.8:27b-q4_K_M`) on one rented RunPod A100 80GB, Ollama 0.40.11, `generate_notes.py` with the stage-3 settings (prompt v3, greedy, thinking off), on the 25 grid consultations. In the same rental session, the human-transcript column is regenerated first, then four stress columns: {5 dB, 0 dB} × {Whisper, Qwen3-ASR}, mixed channel. 125 notes and 125 judge calls (judge protocol v1).

**Analysis, beyond stated-fact recall and the contradiction rate**: attribute note errors to ASR error types — of the facts missing from a note, how many fall in stretches the ASR deleted; of the contradicted facts, how many match a substitution — comparing Qwen3-ASR (more deletions) and Whisper (more substitutions) at 0 dB. Key cases focus on negation flips that reach the note.

**Run** (2026-10-28): RunPod A100-SXM4 80GB, Ollama 0.40.11, about 46 minutes for 125 notes (median about 21 s per note); environment and log in `outputs/notes-stress/stress-qwen3.8-27b/` (not committed). Judging: 125 calls, frozen v1 protocol, with the grid's cached fact lists (checked byte-identical). Results in `results/notes/stress/qwen3.8-27b/`.

**Regeneration check**: the regenerated human column differs from the grid's 27B human column in 2 of 563 stated-fact labels (0.4%), against 6.8% when the GPU changed (stage 3). In the same environment, regeneration noise is negligible, so the differences below are due to the transcripts.

#### Recall and contradictions (stated facts, 563 facts, 25 consultations)

| Source | Stated-fact recall | vs human transcript | Contradicted | vs human transcript |
|---|---|---|---|---|
| Human transcript (regenerated) | 89.3% | — | 1.6% | — |
| *Clean, Whisper (stage-3 grid)* | *86.3%* | *−3.4 vs grid human* | *3.4%* | |
| *Clean, Qwen3-ASR (stage-3 grid)* | *88.8%* | *−0.9 vs grid human* | *2.5%* | |
| S3 5 dB, Whisper | 83.5% | −5.9 [−8.8, −2.6] | 3.6% | +2.0 [+0.7, +3.2] |
| S3 5 dB, Qwen3-ASR | 83.5% | −5.9 [−8.6, −3.3] | 3.6% | +2.0 [+1.0, +3.1] |
| S3 0 dB, Whisper | 75.0% | −14.4 [−18.8, −9.8] | 6.2% | +4.6 [+2.7, +6.4] |
| S3 0 dB, Qwen3-ASR | 75.1% | −14.2 [−17.1, −11.0] | 8.2% | +6.6 [+4.8, +8.4] |

Clean rows (italic) come from the stage-3 grid, a different rental session; their differences are against the grid's own human column. Intervals are paired bootstrap over consultations (`paired_summary_stated.csv`).

- **Dose-response**: the ASR's cost grows from about −1 to −3 points in clean audio, to −6 at 5 dB, to −14 at 0 dB. From 5 dB to 0 dB alone, recall drops by a further 8.5 [4.1, 13.1] points (Whisper) and 8.4 [5.9, 10.7] (Qwen3-ASR).
- **Compared with the generation model**: on the same 25 consultations, Qwen3.8-27B writes notes with 12.1 [7.8, 16.4] points higher stated recall than Qwen3-14B from the same human transcript (stage 3). At 5 dB the ASR costs about half of that; at 0 dB about the same or more (14.4 vs 12.1, overlapping intervals). **At 0 dB babble, listening is as large a bottleneck as writing.**
- **The two ASR systems end level at both SNRs**: Qwen3-ASR − Whisper recall +0.0 [−3.7, +3.4] at 5 dB and +0.2 [−4.1, +4.4] at 0 dB. Qwen3-ASR's WER advantage at 5 dB, and Whisper's at 0 dB, do not reach the notes.
- **Contradictions grow with noise**, from 1.6% to 6–8% of stated facts. At 0 dB Qwen3-ASR has more than Whisper (+2.0 [−0.2, +4.1] points), the opposite of what its higher deletion rate suggested.

#### Attribution to ASR error types

`scripts/attribute_note_errors.py` locates each stated fact's supporting quote in the transcript (92–99% located per group) and measures the ASR's deletion and substitution rates in that utterance. Groups, against the human-transcript note: **kept** (present in both), **lost** (present → missing), **contradicted** (newly contradicted). Results: `attribution/attribution_summary.csv`.

| Source | Group | Facts | Deletion rate | Substitution rate | Utterance ≥ 50% deleted |
|---|---|---|---|---|---|
| 0 dB Whisper | kept | 409 | 17% | 12% | 8% |
| | lost | 68 | 28% | 26% | 21% |
| | contradicted | 28 | 25% | 24% | 19% |
| 0 dB Qwen3-ASR | kept | 406 | 19% | 11% | 10% |
| | lost | 62 | 32% | 21% | 28% |
| | contradicted | 38 | 24% | 24% | 11% |
| 5 dB Whisper | kept | 451 | 13% | 8% | 6% |
| | lost | 41 | 31% | 11% | 20% |
| | contradicted | 13 | 16% | 10% | 8% |
| 5 dB Qwen3-ASR | kept | 454 | 10% | 9% | 4% |
| | lost | 37 | 18% | 20% | 11% |
| | contradicted | 13 | 28% | 17% | 17% |

- **Lost facts sit where the ASR dropped speech.** Their utterances have far higher deletion rates than kept facts, and about three times as often lost at least half their words. For Qwen3-ASR at 0 dB this is the clearest pattern: 28% of lost facts sit in a mostly deleted utterance, against 11% of its contradicted facts.
- **Contradicted facts sit where the ASR misheard**: substitution rates are double those of kept facts for both models at 0 dB.
- **But the mapping is not clean.** Lost facts also sit in stretches with more substitutions, and contradicted facts in stretches with more deletions. Deleting a single "no" turns a negative into a positive, so a deletion can produce a contradiction (case N5 below); and an LLM decoder can turn a masked "No" into a fluent "Yeah", a substitution that reads like a confident answer (case N1). The prediction "Qwen3-ASR's extra deletions show up as missing facts, Whisper's errors as contradicted facts" does not hold at the note level: both lose the same share of facts, and Qwen3-ASR has more contradictions.
- Numbers of contradicted facts are small (13–38 per source); no intervals are given for this table. The quote is matched to one utterance by word overlap; a very short quote such as "No." can match the wrong utterance.

#### Negation flips that reach the note

20 negative facts are contradicted in an ASR note but not in the human note. Examples, checked against the ASR text (times in the original timing):

| # | Consultation · time | Said | ASR | Note |
|---|---|---|---|---|
| N1 | day5_consultation01 · 282 s | Doctor: "And do you smoke?" Patient: "No." Doctor: "Do you take any other drugs of any sort?" Patient: "No." | **Qwen3-ASR, 0 dB**: "Do you smoke? **Yeah.** Do you take any other drugs of any sort? **Yeah.**" (Whisper at 0 dB: correct) | "Smokes" |
| N2 | day5_consultation05 · 261 s | "Uh, no back pain. No, I typically don't suffer from back pain, so, no." | **Whisper, 0 dB**: "not back pain, no, I think it's **just some back pain**" | "lower back pain" |
| N3 | day5_consultation05 · 301 s | "Uh, so, I don't smoke. I drink…" | **Whisper, 0 dB**: "So I **go smoking**, but I go, let's say, four times a week" | "Smokes and drinks alcohol" |
| N4 | day4_consultation05 · 106 s | "I have N, N, NK, NKDA allergy" (no known drug allergies) | **Qwen3-ASR**: "I have an an an **KBA** allergy" (5 dB); "an **aneka** allergy" (0 dB) | "Allergy to KBA"; "Allergy to 'aneka'" — an invented allergy |
| N5 | day4_consultation05 · 500 s | "I didn't have any fever recently… I don't think so" | 34–40% of the utterance's words deleted in three of the four noisy transcripts | "possible low-grade fever" (Qwen3-ASR 5 dB); "reports a low-grade fever" (Whisper 0 dB); "mild fever" (Qwen3-ASR 0 dB) |

- N1 is an LLM-decoder failure: Qwen3-ASR writes a fluent, plausible "Yeah" where the noise masked "No", twice in a row. Whisper keeps both answers at the same SNR.
- N2 and N3 are in day5_consultation05, the consultation of stage-3 case B1 (not → also); at 0 dB it gains two more flipped negatives.
- N4 shows a term error becoming a clinical claim: "NKDA" is unfamiliar to the recogniser, and the note-writer turns the made-up word into a drug allergy.

## 6. Limitations

- **Synthetic overlap is not real interruption**: real interruptions change how people speak (louder, breaking off mid-sentence); here two recordings are only overlapped in time. Also, p = 1.0 makes every change of speaker an interruption, more extreme than reality.
- **The stressed levels do not represent a real setting**: S1's 2× and 3× and S3's low SNRs are artificial stress, not a particular trauma bay. Only each factor's 1× or no-noise level is the real level.
- **A noise library is not a real trauma bay**: the main condition has only two speech-babble backgrounds (cafeteria and restaurant) and no medical equipment sounds; S3b's alarm material is limited.
- **Not covered: more speakers and the far field.** S2 (a third speaker) and S4 (reverberation / far-field microphones) were dropped for time. A trauma bay has both, so these are the first next steps:
  - S2: insertions of the third speaker's words, and whether Whisper writes in background speech more readily than Qwen3-ASR (prediction 2);
  - S4: room impulse responses with a per-speaker distance, to test whether the speaker farther from the microphone is hit harder (prediction 4).
- **One stressor at a time**: each factor was swept alone. Real settings combine overlap, noise and distance, and their effects may compound.
