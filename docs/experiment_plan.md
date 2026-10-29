# medical-asr-eval experiment plan (2026-10-27 – 11-06)

> The original plan, written on 2026-10-27 and translated from Chinese. It is kept as written, apart from two personal details removed from sections 0 and 1; later decisions are recorded where they were made: `docs/stage3-llm-plan.md` (generation models, GPU rental), `docs/stage3-grid-results.md` (note grid) and `docs/stress-test.md` (stress test, added after this plan).

## 0. Goal and research question

**Goal**: by Friday 6 November, produce a public repository.

**Core question**: from a multi-speaker, single-microphone recording to a clinical note, is the quality bottleneck in "listening" (ASR) or in "writing" (the LLM that generates the note)? As both ends get stronger, how does the bottleneck shift?

**Approach**: a two-dimensional grid:

- ASR side: existing models + 2026 frontier models;
- LLM side: generation models of different sizes.

Every configuration gets an error-composition analysis at the ASR level and at the note level.

## 1. Fixed rules (for the whole project)

- **Development / test sets**: the first 10 consultations (day 1) are used only to tune settings and fix methods; final numbers are reported only on the 47 test consultations.
- **One GPU job at a time**: never two models on the GPU at once. Speed figures are taken only with the GPU to itself.
- **One normalisation**: after the normaliser is fixed in stage 1, every model and every condition is scored with the same rules; both raw and corrected WER are kept.
- **Frozen judging**: after stage 1, the judge prompts and each consultation's fact list do not change, and the version number is recorded. Any change means re-judging everything.
- **Fixed note-generation settings**: temperature 0, fixed seed, thinking mode off (the same for every LLM; where a model does not support this, say so).
- **Every LLM has its own noise floor**: for the same LLM, the difference between "human transcript" and "human transcript with only the surface form changed", used to judge whether the ASR's effect exceeds noise.
- **Own resources only**: judging uses the user's personal Claude subscription (first confirm with /status that the personal account is logged in).
- **Commit after each stage**; raw audio, virtual environments and model files are not committed.
- **Anything that needs the user's decision** (spending money, quotas, choices between approaches): stop and ask; do not decide alone.

## 2. Status (as of the early hours of 10/27)

- Test set, 47 consultations: transcription, evaluation, overlap analysis and negation analysis done for Whisper large-v3 (VAD + no previous-text conditioning) and Parakeet TDT 0.6B.
- Note level: Qwen3 14B generation + blind Claude judging, with the noise decomposition done (human, human re-judged, surface form only, speaker labels removed, mixed-channel ASR, separated-channel ASR).
- ASR error-composition analysis done; note error-composition analysis (checking whether each fact was said in the conversation) running.
- Uncommitted changes on the `test47-final` branch.

## 3. Stage plan

### Stage 1: wrap-up and preparation (10/27)

| # | Task | Output / acceptance |
|---|---|---|
| 1.1 | Finish the note error-composition analysis (check against the conversation + classify) | `results/notes/test47/error_composition/` |
| 1.2 | Commit `test47-final`, merge into main | PR merged |
| 1.3 | Fix the normaliser: after the Whisper normaliser, add an equivalence table (ok/okay, alright/all right, mum/mom, "oh" turned into 0, etc.) in `evaluate.py`; recompute all existing results | the main results table has "raw WER / corrected WER" columns |
| 1.4 | VAD padding check (dev set): try 2–3 larger `speech_pad_ms` values and look at the error rate of the first word of each utterance and overall WER | a small table; if clearly better, re-run Whisper on the test set with the new value |
| 1.5 | Freeze the judging protocol: version the judge prompts and fact lists | `docs/judge_protocol.md` states the version |

### Stage 2: ASR side (10/27 – 10/28)

| # | Task | Output / acceptance |
|---|---|---|
| 2.1 | Check whether these models run on Windows + 5080 (16 GB): Cohere Transcribe, IBM Granite Speech 4.1 2B, Qwen3-ASR-1.7B, NVIDIA Canary-Qwen 2.5B. Record the Hugging Face name, licence, inference method and memory needs | a new section in the setup notes; for models that do not install, the reason |
| 2.2 | For the models that run: all 47 test consultations × three tracks. Segment long audio as each model requires, without introducing new joining errors (segmentation documented) | one outputs folder per model |
| 2.3 | For every model: WER (raw + corrected), substitutions/deletions/insertions, deletion rate inside and outside overlap, ASR error composition (word class, substitution type, position), negation analysis, time per audio minute | collected into `results/test47/comparison.csv` |
| 2.4 | Choose the "best 2026 ASR" (mainly mixed-channel corrected WER, with medical-term error rate as reference) | the reason stated in the summary |

**Common definitions for the ASR error-composition analysis** (the same for every model):

- **Word classes**: backchannels/fillers, function words, ordinary content words, medical terms (scispaCy), numbers and durations, negations (clinical negation / discourse marker), drug names and proper nouns;
- **Substitution types**: spelling variant, split word, inflection, near-homophone, different number value, genuinely wrong word; the 30 most frequent substitution pairs;
- **Position**: inside/outside overlap, utterance start/middle, single-word responses, near `<UNSURE>`, long silence;
- **Denoised WER**: without backchannels, content words only, medical-term error rate, number error rate;
- **False-error estimates**: caused by normalisation; at uncertain reference transcription (upper bound).

**One more item (new lead)**: single-word responses have an error rate of about 60%. Break down the erroneous single-word responses: how many answer a clinical question (the question contains content words about symptoms, drugs, time, etc.) and how many are just backchannels; compare with omissions and reversals at the note level.

### Stage 3: note-side grid (10/29 – 11/1)

**Before starting, the user decides**:

- which open LLM to use for the mid and large tiers (first check the best open models that currently run on 80 GB; give 2–3 candidates with reasons);
- whether to rent a GPU (Runpod, A100 80GB about $1.79/hour), with estimated time and cost;
- whether to do Claude as an "upper reference" note generator, and whether the judging quota is enough.

**Grid** (mixed channel only, closest to a single microphone):

| LLM \ input | Human transcript | Human, surface form only (noise floor) | Whisper, mixed | Best 2026 ASR, mixed |
|---|---|---|---|---|
| Qwen3 14B (5080) | done | done | done | new |
| Mid tier (about 30B) | new | new | new | new |
| Large tier (about 70B, rented GPU) | new | new | new | new |
| Claude (upper reference, optional) | new | new | new | new |

- Each cell first runs 25 test consultations; if a trend appears and the quota allows, fill up to 47.
- All generation uses the same prompt (chat API, rules in the system message), temperature 0, fixed seed.
- When renting: prepare the scripts, model names and data before starting the machine; batch generation with vLLM; stop or delete the pod as soon as the run finishes.
- For the Claude-generated tier: judging stays blind; the README states the potential bias of "generator and judge from the same family", and the user spot-checks more notes.

**Note error-composition analysis for every cell**:

- **Facts not written**: never said in the conversation / conversation contradicts the clinician's note / only partly said / missed by the generation model itself (the human version misses it too) / missed only by that ASR;
- **Extra content**: contradicting the clinician's note, invented negative findings, other additions;
- **Against that LLM's noise floor**: paired differences + bootstrap 95% intervals;
- **Key error cases**: meaning flips (negations, numbers, "not ↔ also" and the like) listed separately, with time and original text.

### Stage 4: summary (11/1)

| # | Task | Output |
|---|---|---|
| 4.1 | Main results table: every ASR model | `results/summary/asr_main.csv` |
| 4.2 | Grid figure: ASR on the x-axis, LLM on the y-axis; each cell the share of facts missed or reversed relative to the human transcript (with noise floor) | `results/summary/grid_heatmap.png` |
| 4.3 | Key-case table: 2–3 examples per kind of dangerous error, with deep links | `results/summary/critical_cases.csv` |
| 4.4 | Comparison viewer: updated to the final set of methods | `results/viewer/` |

### Stage 5: README and release (11/2 – 11/5)

README structure (English):

- **Motivation**: automatic documentation in a trauma bay; PriMock57 as an open proxy (two people, simulated single microphone) and its limits;
- **Pipeline diagram**: audio → ASR → joining → LLM note → blind judging;
- **Main findings**:
  - default decoding settings exaggerate hallucination (loops disappear with previous-text conditioning off); once fixed, differences between architectures are small;
  - the cost of mixing is concentrated in overlaps, as dropping the speaker who comes in (consistent with the observation in *Who Spoke What When?* 2026);
  - nearly half of WER is false errors (inconsistent spelling, uncertain reference transcription);
  - note level: the ASR's effect vs generation noise; how the bottleneck shifts as the LLM gets stronger (grid figure);
  - key error cases: dangerous errors that averages hide;
- **Method details**: dev/test split, normalisation rules, judging protocol, noise decomposition;
- **Limitations**: two-person conversation ≠ trauma bay; reference transcripts contain errors; the judge is an LLM; sample size;
- **Next steps**: stress test (synthetic multi-speaker overlap, noise, reverberation), speaker-conditioned recognition (DiCoW) or separation, medical-domain fine-tuning, semantic metrics (tcpSemER), audio-visual speaker diarisation, automatic flagging of high-risk content (negation + low confidence) for review;
- Reproduction steps and environment; data source and licence (CC BY 4.0).

Make the repository public by 11/5, after checking that it contains no keys, personal paths or raw audio.

## 4. What the user must do personally (cannot be delegated)

- Listen to 40 sampled insertions: `results/test47/listening_sample.csv`;
- Spot-check 20 judgements: `results/notes/test47/spotcheck.csv`;
- Use the comparison viewer to listen to typical errors: loops, words dropped in overlap, negation flips, single-word responses;
- Decisions before stage 3: LLM choice, whether to rent a GPU, Claude quota;
- Read the README through before finalising, so that every conclusion can be explained in their own words.

## 5. Risks and fallbacks

| Risk | Fallback |
|---|---|
| New 2026 models do not install on Windows | run the ones that install first; if none do, use Canary-Qwen or keep only Whisper + Parakeet, and say so in the README |
| Not enough judging quota | reduce each grid cell to 25 consultations; prioritise each LLM's noise floor and the "best ASR" column |
| Problems running the large model on a rented GPU | keep only Qwen3 14B and the mid tier; put the large tier under next steps |
| Not enough time | stage 3 only the mid-tier LLM row; README writing must start on 11/2 |
