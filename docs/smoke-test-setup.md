# Local smoke test: environment and configuration

Recorded 2026-10-26. How the environment on this machine was set up, how each round was run, and the known issues, so the work can be reproduced or moved to another machine.

## 1. Hardware and system

| Item | Configuration |
|---|---|
| GPU | NVIDIA GeForce RTX 5080 Laptop, 16 GB VRAM, Blackwell (sm_120) |
| Driver | 610.62 (CUDA 13.3) |
| OS | Windows 11 Home (Chinese edition) |
| System-wide CUDA Toolkit | Not installed. CUDA runtime libraries are pip-installed inside each virtual environment |
| ffmpeg | Not installed and not needed (audio is wav; PyAV has its own decoder) |

## 2. File locations (all on drive D)

| Path | Contents |
|---|---|
| `D:\medical-asr-eval` | Repository |
| `D:\Python311` | Python 3.11.9 (installed with winget, not on the system PATH; the existing Python 3.13 is untouched) |
| `D:\cache\huggingface` | Model cache (`HF_HOME`) |
| `D:\cache\pip` | pip cache |
| `data\primock57` | PriMock57 raw data (all 57 consultations) |
| `data\prepared_3min` | First 3 consultations, each cropped to about the first 3 minutes |
| `data\prepared_full10` | First 10 consultations, full length: the **dev set**, used to choose decoding settings and analysis methods |
| `data\prepared_test47` | Remaining 47 consultations, full length: the **test set**; final numbers are reported on this set only |
| `D:\Tools\GitHubCLI` | GitHub CLI (`gh`), logged in as Fw93810 |
| `D:\Tools\Ollama`, `D:\cache\ollama` | Ollama and its models (user environment variable `OLLAMA_MODELS=D:\cache\ollama`) |
| `D:\Tools\ClaudeCode` | Claude Code CLI, logged in with a personal subscription, called by `judge_notes.py` |
| `outputs\<run>` | Transcription JSON per run |
| `results\<run>` | Evaluation CSVs per run |
| `results\viewer\index.html` | Side-by-side listening page |

## 3. Virtual environments

The dependencies conflict, so there are six environments, all based on `D:\Python311`:

| Environment | Used for | Key versions | Why separate |
|---|---|---|---|
| `.venv` | faster-whisper transcription, viewer page | faster-whisper 1.2.1, ctranslate2 4.8.4, cuBLAS 12.9, CUDA runtime 12.9, cuDNN 9.27, numpy 2.4.6 | Main environment, installed from requirements.txt |
| `.venv-sci` | Medical-term extraction with scispaCy, evaluate.py | scispacy 0.6.2, spaCy 3.7.5, en_core_sci_sm 0.5.4, jiwer 4.0.0, numpy 1.26.4 | scispaCy needs numpy 1.x and would downgrade numpy in the main environment |
| `.venv-nemo` | Parakeet (`--backend parakeet`) | PyTorch 2.11.0+cu128, NeMo 3.0.0, numpy 2.4.6 | NeMo has many dependencies and needs PyTorch with CUDA |
| `.venv-hf` | Granite Speech, Cohere Transcribe (`--backend granite/cohere`) | PyTorch 2.11.0+cu128, transformers 5.21.0, accelerate 1.15 | Cohere needs transformers ≥ 5.4 |
| `.venv-qwen` | Qwen3-ASR (`--backend qwen3asr`) | PyTorch 2.11.0+cu128, qwen-asr 0.0.6, transformers 4.57.6 | `qwen-asr` pins transformers 4.57, which conflicts with Cohere |
| `.venv-canary` | Canary-Qwen (`--backend canary-qwen`) | PyTorch 2.11.0+cu128, NeMo 3.1.0 development version (GitHub), peft 0.21 | Needs the NeMo development version; the working Parakeet environment is left alone |

### Making faster-whisper find the CUDA libraries

On Windows, ctranslate2 looks for `cublas64_12.dll` and `cudnn*64_9.dll` on the PATH. The pip-installed NVIDIA libraries are not added to the PATH, so the main environment has a start-up hook:

`.venv\Lib\site-packages\_cuda_dlls.pth`

Every time this environment's Python starts, the hook:
- adds `site-packages\nvidia\{cublas,cudnn,cuda_runtime,cuda_nvrtc}\bin` to the PATH and the DLL search path;
- sets `HF_HOME` to `D:\cache\huggingface` by default.

It also works with `-I`. Restore this file if the main environment is rebuilt.

The other environments do not need the hook (PyTorch ships its own CUDA libraries). `.venv-nemo` and `.venv-sci` do not set `HF_HOME` either, so set `HF_HOME=D:\cache\huggingface` before running them, or models are downloaded to drive C.

### GPU checks

- faster-whisper large-v3 loads and transcribes in float16 on CUDA. There were no errors on the 50-series GPU, so the fallback (transformers Whisper) was not needed.
- PyTorch 2.11+cu128 recognises sm_120 (`torch.cuda.is_available()` is True). Parakeet-TDT-0.6B-v2 transcribes normally.

## 4. Runs

| Run | Data | Model | Settings | Environment | Status |
|---|---|---|---|---|---|
| `fw-large-v3` | 3 × 3 min | large-v3 | Defaults (beam 5, no VAD) | `.venv` | Done |
| `fw-large-v3-turbo` | 3 × 3 min | large-v3-turbo | Defaults | `.venv` | Done |
| `fw-large-v3-vad` | 3 × 3 min | large-v3 | `--vad` | `.venv` | Done |
| `full10-large-v3` | 10 full | large-v3 | Defaults | `.venv` | Done |
| `full10-large-v3-vad` | 10 full | large-v3 | `--vad` | `.venv` | Done |
| `full10-parakeet` | 10 full, mixed channel only | parakeet-tdt-0.6b-v2 | Defaults (full attention) | `.venv-nemo` | Done (re-run with the GPU to itself) |
| `full10-vad-nocond` | 10 full | large-v3 | `--vad --no-condition-on-previous-text` (H1b) | `.venv` | Done |
| `full10-vad-nocond-hst2` | 10 full | large-v3 | As above plus `--hallucination-silence-threshold 2` (turns on word timestamps) | `.venv` | Done |

Summary tables: `results/full10/comparison.csv`, `results/full10/top_insertions.csv` (scispaCy terms); `results/lexicon/full10/` is the same data scored with the built-in term list.

In the `full10-parakeet` JSON the `model` field says `base`: at the time, the parakeet backend of transcribe.py did not override the `--model` default. The model actually used was `nvidia/parakeet-tdt-0.6b-v2`. Fixed for later runs.

Settings shared by all Whisper runs: `language="en"`, float16, beam size 5, no initial prompt. VAD and previous-text conditioning as in the table above; the final setting chosen on the dev set is VAD on, previous-text conditioning off. Three tracks: doctor channel, patient channel, and the mixed mono channel (the two channels summed and peak-normalised to −1 dBFS).

### Test set (47 consultations, final settings only, run once)

| Run | Model | Settings | Purpose |
|---|---|---|---|
| `test47-vad-nocond` | large-v3 | `--vad --no-condition-on-previous-text`, three tracks | Main result |
| `test47-parakeet-local` | parakeet-tdt-0.6b-v2 | `--local-attention`, three tracks | Architecture comparison |
| `test47-vad-nocond-wt` | large-v3 | As the main result plus `--word-timestamps`, doctor and patient channels only | Interleaving the two channels for separated-channel notes |

Turning on word timestamps changes faster-whisper's decoding windows, so the text of `test47-vad-nocond-wt` is not identical to `test47-vad-nocond`: about 4.4% of words differ between the two runs. WER is almost the same (doctor 11.2% vs 11.0%, patient 13.0% vs 13.0%), so this is decoding variation, not a quality difference.

Summary table: `results/test47/comparison.csv`. Other analyses: `results/test47/overlap/` (overlap, Whisper), `results/test47/overlap-parakeet/`, `results/test47/negations/` (negations), `results/test47/listening_sample.csv` (40 insertions awaiting manual labels). Viewer page: `results/viewer-test47/`.

### Normalisation: raw and corrected WER

The Whisper English normaliser writes some words inconsistently, which is counted as errors. `evaluate.py --equivalence` applies a fixed equivalence table after normalisation:

| Mapped to | Original forms |
|---|---|
| okay | ok, o k, 0 k ("O.K." becomes "0 k" in the normaliser) |
| alright | all right |
| mom, mommy | mum, mummy |
| 0 | ohh, ooh (the normaliser turns "oh" into "0") |

Every run is scored both ways: raw results in `results/<run>/`, corrected results in `results/equiv/<run>/`; the main table (`comparison.csv`) shows `wer` and `wer_corrected` side by side. Raw WER is for comparison with the literature; corrected WER reflects actual recognition. Errors at places the annotators marked as uncertain are reported separately as an upper bound and are not subtracted from WER.

### 2026 ASR models

| Model | Hugging Face | Licence | Environment | Installation and runtime issues |
|---|---|---|---|---|
| Granite Speech 4.1 2B | `ibm-granite/granite-speech-4.1-2b` | Apache 2.0 | `.venv-hf` | None. The model card does not say how to handle long audio; the shared chunk plan is used |
| Cohere Transcribe 03-2026 | `CohereLabs/cohere-transcribe-03-2026` | Apache 2.0, **gated** | `.venv-hf` | Agree to share contact details on the model page with a Hugging Face account, and run `hf auth login` locally (the token is stored in `D:\cache\huggingface`). Downloads return 403 until then |
| Qwen3-ASR-1.7B | `Qwen/Qwen3-ASR-1.7B` | Apache 2.0 | `.venv-qwen` | Its library `qwen-asr` pins transformers 4.57, which conflicts with Cohere, hence a separate environment |
| Canary-Qwen 2.5B | `nvidia/canary-qwen-2.5b` | CC-BY-4.0 | `.venv-canary` | Needs the NeMo development version: `pip install "nemo_toolkit[asr] @ git+https://github.com/NVIDIA/NeMo.git"`. Installing `[asr,tts]` as the model card says fails (`pyopenjtalk` in tts needs a CMake build on Windows); only `pip install peft` is needed in addition |

**Shared chunk plan**: all four models only suit short inputs, so `plan_chunks.py` makes one chunk plan (`outputs/chunks/test47/`):
- Silero VAD finds speech regions; cuts happen only at pauses;
- chunks are at most 30 s, with 0.3 s padding at each end;
- continuous speech longer than 30 s is cut at its quietest 100 ms frame.

The 141 test-set files become 2,482 chunks, longest 30.6 s, keeping 84.8% of the audio; about 0.7% of reference words fall outside every chunk (by estimated word times). Each chunk is decoded on its own and its output segment takes the chunk's start and end times. Cohere's processor splits inputs longer than 35 s by itself; all our chunks are shorter, so this never triggers.

To keep chunking out of the model comparison, Whisper and Parakeet were also run with the same chunk plan (`test47-whisper-chunked`, `test47-parakeet-chunked`); their own best settings (Whisper's built-in VAD, Parakeet on whole files) are kept as well.

**One chunk at a time, no batching**: `--batch-size` decodes several chunks at once and is 3–4× faster, but the output differs from one-at-a-time decoding (on the same file, 1.6% of words differ for Granite, 0.2% for Qwen3-ASR), because short chunks are padded to a common length in a batch. For comparability, all reported runs use `--batch-size 1`.

**Test-set results** (47 consultations; WER raw → corrected; speed in seconds per audio minute on the RTX 5080 laptop, one chunk at a time):

| Run | Doctor | Patient | Mixed | Mixed: sub / del / ins | Mixed: deletion in / out of overlap | Mixed s per audio min |
|---|---|---|---|---|---|---|
| `test47-qwen3-asr-1.7b` | 9.5 → 6.1 | 10.7 → 9.5 | **11.0 → 8.6** | 5.0 / 4.2 / 1.8 | 20.3 / 2.9 | 5.5 |
| `test47-canary-qwen-2.5b` | 10.4 → 7.0 | 12.0 → 10.9 | 12.0 → 9.7 | 5.2 / 4.6 / 2.2 | 21.3 / 3.3 | 5.7 |
| `test47-parakeet-chunked` | 10.5 → 7.2 | 12.6 → 11.5 | 12.3 → 10.0 | 5.1 / 5.1 / 2.1 | 21.6 / 3.8 | 0.25 |
| `test47-vad-nocond` (Whisper, built-in VAD) | 11.0 → 7.8 | 13.0 → 11.9 | 12.5 → 10.3 | 5.0 / 5.7 / 1.9 | 25.3 / 4.1 | 5.1 |
| `test47-parakeet-local` (whole files) | 11.4 → 7.9 | 14.5 → 13.4 | 12.9 → 10.7 | 4.9 / 6.2 / 1.8 | 22.7 / 4.9 | 0.16 |
| `test47-whisper-chunked` | 11.2 → 8.0 | 14.6 → 13.5 | 13.0 → 10.8 | 5.0 / 6.0 / 2.0 | 23.4 / 4.6 | 5.0 |
| `test47-cohere-transcribe` | 11.5 → 8.2 | 15.1 → 14.1 | 13.7 → 11.5 | 4.9 / 6.9 / 2.0 | 22.3 / 5.6 | 1.05 |
| `test47-granite-4.1-2b` | 12.1 → 9.0 | 23.5 → 22.5 | 14.7 → 12.6 | 4.9 / 8.4 / 1.4 | 30.3 / 6.7 | 5.5 |

- Qwen3-ASR-1.7B is best on all three tracks, and also has the lowest medical-term error rate (mixed 5.6%, Whisper 6.8%) and clinical-negation loss (mixed 2.2%, Whisper 5.0%).
- The shared chunk plan helps Parakeet (mixed 12.9 → 12.3, patient 14.5 → 12.6) and costs Whisper a little (mixed 12.5 → 13.0): Whisper's own VAD segmentation suits it better.
- Granite has 6 long repetitions on the patient channel (1,372 words in total, e.g. hundreds of "no" or "yeah" in a row), which pushes its patient WER to 23.5%; apart from the repetitions, its deletion rate is also the highest.
- Overlap: every model deletes 10.6–13.9 points more on the mixed channel than on the separated channels, and the speaker who comes in loses far more than the speaker who is already talking (+15.5–20.0 vs +6.4–10.5). This is a property of the mixed channel that a different model does not fix.
- Cohere is the fastest of the four new models (1.05 s per minute; Parakeet is faster still), but it deletes more, especially on the patient channel.
- Details: `results/test47/comparison.csv`, `results/test47/overlap-<model>/`, `results/test47/error_composition/`, `results/test47/negations/`.

### VAD padding (dev set)

To check whether the high error rate on the first word of an utterance comes from VAD clipping utterance starts, the dev set was run with `speech_pad_ms` 400 (default), 800 and 1500, and without VAD (all with previous-text conditioning off). The first-word error rate barely changes across the four (mixed channel 36.1–36.8%) and is just as high without VAD, so VAD is not the cause. 60% of first-word errors are backchannels, and 58% of the substitutions are spelling variants such as "OK/okay". WER changes are within noise, so the test set keeps the default padding. Results: `results/full10/vad_padding/`.

### Note-level evaluation

1. `generate_notes.py`: `qwen3:14b` (4-bit) in local Ollama, temperature 0, fixed seed, thinking off, prompt version v3. Three notes per consultation: human transcript; separated-channel ASR (`test47-vad-nocond-wt`, the two channels merged into labelled speaker turns using word timestamps); mixed-channel ASR (`test47-vad-nocond`, no speaker labels).
   - The channels were first interleaved by sentence, but Whisper without previous-text conditioning often outputs no punctuation, so one "sentence" spans several turns and questions and answers get out of order. That lowered note recall for the separated-channel source by 3.5 points. The old results are kept in the `*-separated-by-sentence` folders.
   - Noise controls:
     - `human_rejudge`: the same human-transcript note judged again (judge noise);
     - `human_plain`: the human transcript passed through the Whisper normaliser (generation variation from surface form alone);
     - `human_unlabelled_plain` and `asr_mixed_plain`: identical surface form on both sides, differing only in the recognised words (pure ASR error);
     - `asr_separated_plain`.
   - Paired comparison: `compare_notes.py`, one difference per consultation, bootstrap 95% interval; results in `results/notes/test47/paired_summary.csv`.
2. `judge_notes.py`: the Claude Code CLI called non-interactively (`claude -p`, no tools, JSON-schema output).
   - Each clinician note is first split into a fact list (once per consultation); then each candidate note is judged against it.
   - The judge never sees which source a note came from, and jobs run in shuffled order (seed 0).
   - Every call records the model actually used (`claude-opus-5-5` in this round). Overload errors are retried automatically.
3. The human-transcript notes are the baseline. The clinician's notes themselves differ from the conversation (e.g. the conversation says "three to four days", the note "3–5 days"), so what matters is how much more the ASR sources get wrong than the human transcript.
4. Manual spot check: `results/notes/test47/spotcheck.csv`, per-fact judgements for 20 notes; fill in the `your_label` column.
5. **The judging protocol is frozen (judge v1).** The following no longer change:
   - the system prompt, the fact-splitting and judging prompts, and the two JSON schemas in `judge_notes.py`;
   - the per-consultation fact lists under `results/notes/test47/facts/` (split on 2026-10-26, once per consultation).

   All later notes (new LLMs, new ASR) are judged with the same fact lists and prompts. Changing any of these means a new version number and re-judging everything. Judgement JSON files record `judge_version` (files made before v1 lack the field but used the same prompts).

### Reproduction commands (run from `D:\medical-asr-eval`)

```bash
# Data
.venv/Scripts/python.exe -I scripts/download_data.py --out data/primock57 --limit 10
.venv/Scripts/python.exe -I scripts/prep_data.py --src data/primock57 --out data/prepared_full10 --limit 10

# Transcription (Whisper)
.venv/Scripts/python.exe -I scripts/transcribe.py --data data/prepared_full10 --out outputs/full10-large-v3 --model large-v3 --device cuda
.venv/Scripts/python.exe -I scripts/transcribe.py --data data/prepared_full10 --out outputs/full10-large-v3-vad --model large-v3 --device cuda --vad

# Transcription (Parakeet, mixed channel only; set HF_HOME=D:\cache\huggingface first)
.venv-nemo/Scripts/python.exe -I scripts/transcribe.py --backend parakeet --data data/prepared_full10 --out outputs/full10-parakeet --conditions mixed

# Evaluation (scispaCy environment)
.venv-sci/Scripts/python.exe -I scripts/evaluate.py --data data/prepared_full10 --hyp outputs/full10-large-v3 --results results/full10-large-v3 --terms scispacy

# Summary table plus the 10 longest insertions
.venv-sci/Scripts/python.exe -I scripts/aggregate_results.py --results "results/full10-*" --out results/full10 --top 10

# Viewer page
.venv/Scripts/python.exe -I scripts/make_viewer.py --data data/prepared_3min --outputs outputs --out results/viewer
.venv/Scripts/python.exe -I -m http.server 8765 --bind 127.0.0.1
```

Transcription resumes after interruptions: existing outputs are skipped, so re-run the same command.

## 5. Changes relative to the original repository

First round (PR #1 and #2, merged):

- **`scripts/evaluate.py`**
  - Inside/outside-overlap analysis: the intervals where the doctor's and patient's utterances overlap are taken from `utterances.json`, substitutions, deletions and insertions are assigned to inside or outside, and each is divided by that region's reference words. Written to the `ov_*`, `*_rate_in` and `*_rate_out` columns of `wer.csv` and `summary.csv`; `insertions.csv` gains an `in_overlap` column.
    - Note: word times are estimated by spreading each utterance's (or transcript segment's) start and end evenly over its words; they are not real word timestamps.
  - Pronouns such as i, you and we were added to the scispaCy stop list, because en_core_sci_sm tags "I" as an entity.
- **`scripts/aggregate_results.py`** (new): combines result folders into `comparison.csv` and `top_insertions.csv`.
- **`scripts/make_viewer.py`, `scripts/viewer_template.html`** (new): the listening page — play the original audio, see the analysis steps, compare methods side by side.
- **`transcribe.py`**: `--word-timestamps`, `--hallucination-silence-threshold`; run settings recorded in the output.

Test-set round (`test47-final` branch) and later:
- **`analyze_overlap.py`**: who and what is lost in overlaps (speaker, who came in, who is quieter, word class), word by word, separated vs mixed channel.
- **`analyze_negations.py`**: what happens to every negation (correct / deleted / replaced by what), clinical negations vs discourse markers, repeated negations marked.
- **`sample_insertions.py`**: random insertions for manual labelling, each row with a viewer deep link.
- **`generate_notes.py`, `judge_notes.py`, `compare_notes.py`**: note-level evaluation (above).
- **Viewer page**: deep links `#id=…&cond=…&t=…`; `make_viewer.py` gains `--methods`.
- **`evaluate.py`**: `insertions.csv` gains an estimated word time `t_approx_s`.
- **`bootstrap_asr.py`**: paired bootstrap between ASR runs, resampling consultations, for corrected WER, medical-term error rate and clinical-negation loss.
- **`count_repeats.py`**: long repetitions — the same word ≥ 10 times in a row, or a 2–4 word phrase ≥ 5 times in a row.
- Why Qwen3-ASR was chosen: `results/test47/asr_selection.md`. Stage-3 LLM candidates and cost estimates: `docs/stage3-llm-plan.md`.
- **Note grid** (stage 3):
  - `run_grid.sh` generates notes on a rented server;
  - `generate_notes.py` gains `--think` (reasoning effort), `--asr-name` (a second ASR as its own row), `--ids-file` and `--openai-url`;
  - `combine_grid.py` combines the columns;
  - `note_error_composition.py` includes `asr_mixed_qwen3asr`.
  - Results: `docs/stage3-grid-results.md`.

`.claude/` is local only and not committed.

## 6. Known issues

- **Parakeet is slow on long audio.** With full attention (the default), audio longer than about 10 minutes fills the 16 GB of VRAM and speed collapses: a few seconds for short files, over 110 s for a 14-minute file. The test set uses `--local-attention`, about 0.15 s per audio minute.
- **The Ollama server has to be started by hand.** The tray app did not start the server on first launch; it is now run directly with `D:\Tools\Ollama\ollama.exe serve` and must be restarted after a reboot. Do not transcribe while Qwen is running; VRAM is not enough for both.
- **Qwen invents negative findings.** For example "no recent travel" or "no drug allergies" when nobody said so; this happens for all three sources and the judge counts them as `extra_not_mentioned`. Naming examples in the prompt ("do not add travel, allergies") made the model write exactly those.
- **`claude -p` output is not fully deterministic.** Splitting the same clinician note twice gives slightly different fact counts, so the fact list is split once per consultation, cached, and shared by all sources.
- **Do not run two models on the GPU at once.** With Whisper and Parakeet running together, VRAM reaches 15.8/16 GB and both slow down several-fold. Speed figures from that period are not usable: the first 4 consultations of `full10-parakeet`, and `full10-large-v3` from the same period.
- **large-v3 is slower than expected.** Even with the GPU idle, it takes about 10 s per audio minute at about 40% GPU utilisation; the bottleneck may be on the CPU side, not yet investigated. This does not affect WER.
- **Speed figures for the 3-minute batch are also unreliable.** A game was using the GPU (about 6 GB VRAM) at the time.
- **The Hugging Face cache cannot use symlinks.** Developer mode is off on this machine, so the cache falls back to copying files. This takes more disk space but works; set `HF_HUB_DISABLE_SYMLINKS_WARNING=1` to silence the warning.
- **The viewer page must be opened over HTTP.** `python -m http.server` does not support Range requests, so the page loads the whole wav into memory before playing, which makes seeking work. Opening the html file directly makes the browser block the audio.
- **The two term-recall methods are not comparable.** The 3-minute batch used the built-in term list (about 320 terms); later rounds use scispaCy.
- **Write CSVs as UTF-8.** Windows with a Chinese locale writes files as GBK by default. The new models output symbols such as "£", and `evaluate.py` failed while writing `insertions.csv`, leaving it half written (`wer.csv` and `summary.csv` are written before it and were not affected). All CSVs are now written and read as UTF-8; the 3 old GBK files (`insertions.csv` of `full10-large-v3`) were converted.
- **The dev set is harder than the test set.** All 10 dev consultations are from day 1, and their WER is clearly higher than the test set's (e.g. mixed channel 17.2% vs 12.5%). Looking only at the dev set overestimates error rates.
