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

To do.

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

To do. The first to be dropped if time runs out.

## 5. Results

To be added.

## 6. Limitations

- **Synthetic overlap is not real interruption**: real interruptions change how people speak (louder, breaking off mid-sentence); here two recordings are only overlapped in time. Also, p = 1.0 makes every change of speaker an interruption, more extreme than reality.
- **The stressed levels do not represent a real setting**: S1's 2× and 3× and S3's low SNRs are artificial stress, not a particular trauma bay. Only each factor's 1× or no-noise level is the real level.
- **A noise library is not a real trauma bay**: the main condition has only two speech-babble backgrounds (cafeteria and restaurant) and no medical equipment sounds; S3b's alarm material is limited.
