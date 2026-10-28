# medasr-smoke: open-weight ASR on PriMock57 medical consultations

A small, exploratory pipeline: transcribe the PriMock57 mock GP consultations with an
open-weight ASR model and look at WER, medical-term recall and inserted words
(possible hallucinations). The aim is to see the outputs and the kinds of errors, not to tune anything.

```
download_data.py  ->  prep_data.py  ->  transcribe.py  ->  evaluate.py
 (repo + LFS audio)   (doctor/patient/    (faster-whisper    (WER, term recall,
                       mixed wav + refs)   or Parakeet JSON)  insertions -> CSV)
```

## Data: PriMock57

- Source: https://github.com/babylonhealth/primock57 (papers: arXiv 2204.00333, 2204.00447).
- **License: CC BY 4.0** (`LICENSE.md` in the repo). You may reuse and redistribute it with attribution; cite the ACL 2022 paper.
- 57 mock primary-care consultations (7 Babylon clinicians; Babylon employees playing patients from case cards).
  The **case cards are not in the repo**. The README only says they were used.
- Layout:
  - `audio/` has 114 wav files, `dayD_consultationNN_{doctor,patient}.wav`: **a separate file per speaker**,
    16 kHz, mono, 16-bit PCM. The two files of a consultation are time-aligned (lengths can differ by a few ms).
    Total 8 h 38 min per channel (about 2.0 GB). The original source was Opus video-call audio.
  - `transcripts/` has 114 Praat TextGrid files (long format), one IntervalTier per speaker file. Each tier has
    utterance intervals with `xmin`/`xmax` in seconds and the text. The speaker comes from the filename (tier names are inconsistent:
    mostly "Speaker"). Tags: `<UNSURE>...</UNSURE>` (1132), `<UNIN/>` (1359), `<INAUDIBLE_SPEECH/>` (814).
    The transcripts are verbatim, with fillers ("um", "uh").
  - `notes/` has 57 JSON files: `day`, `consultation`, `presenting_complaint`, `note` (the clinician's free-text SOAP-style note),
    `highlights` (the clinician's highlighted key phrases).
  - `consultation_checklists/` has 27 xlsx files (Clinician_1: 20, Clinician_2: 7): checklist items marked
    critical/non-critical and per-sentence correctness of generated notes, from the note-generation human evaluation.
  - `human_eval_data/` has the note-generation human evaluation (results.csv, metric-scores.json, ...).
  - `scripts/` has the authors' helpers (TextGrid to transcript, sox mixing, utterance extraction for sclite).
- **Audio is stored with Git LFS.** A plain `git clone` without LFS gives 133-byte pointer files.
  The repo says to install git-lfs and clone. `download_data.py` instead clones with `GIT_LFS_SKIP_SMUDGE=1`
  and fetches each wav from `https://media.githubusercontent.com/media/babylonhealth/primock57/main/audio/<file>`,
  verifying the sha256 and size from the pointer. This works on Colab and in sandboxes where the LFS batch API is blocked.

## What each script does

| file | purpose |
|---|---|
| `scripts/download_data.py` | clone repo (text only) + download/verify LFS audio (`--limit`, `--ids`) |
| `scripts/prep_data.py` | per consultation: `doctor.wav`, `patient.wav`, `mixed.wav` (sum, peak-normalised to -1 dBFS), `ref_{doctor,patient,mixed}.txt` (mixed = utterances merged by start time), `ref_mixed_speakers.txt`, `utterances.json`. `--max-seconds` crops at a point that is silent in both channels |
| `scripts/transcribe.py` | faster-whisper (default; `--model tiny/base/small/large-v3/large-v3-turbo`, `language="en"`, `--initial-prompt`, `--vad`) or `--backend parakeet` (NeMo `nvidia/parakeet-tdt-0.6b-v2`). One JSON per audio file with segments, timestamps and runtime. Resumable |
| `scripts/evaluate.py` | Whisper English normaliser, then jiwer WER (sub/del/ins); medical-term recall; insertion runs with timestamps. Writes `wer.csv`, `summary.csv`, `insertions.csv`, `missed_terms.csv` |
| `scripts/medical_terms.txt` | fallback term lexicon (about 320 general primary-care terms, written independently of the transcripts) |
| `scripts/make_colab_notebook.py` | regenerates `colab_full_run.ipynb` with the current scripts embedded |
| `colab_full_run.ipynb` | Colab GPU notebook: all 57 consultations, large-v3, CSVs saved to Drive |

### Metric details and caveats
- **WER** is computed on Whisper-normalised text: lower case, no punctuation, fillers removed, numbers and spelling standardised.
  The quirk to know: the normaliser also merges number sequences ("six, seven times a day" becomes "67 times a day") in both the reference and the hypothesis.
- **Mixed condition reference**: utterances from both speakers are sorted by start time. When speakers overlap
  (about 19 to 57 s of overlap per consultation in the three we looked at), the "right" word order is not well defined, so mixed WER is slightly pessimistic.
- **Term recall** = the share of distinct reference medical terms that also appear as a contiguous word sequence in the hypothesis.
  It uses scispaCy `en_core_sci_sm` entities when that model loads, otherwise the lexicon. The `term_extractor` column records which was used.
  The two give **different numbers and must not be compared with each other**. scispaCy's small model also tags many non-medical spans.
- **Insertions**: hypothesis word runs aligned to nothing in the reference, with the segment start time and context.
  Sort by `n_words` to find hallucination candidates (e.g. repeated phrases or "thank you for watching").

## Run locally (CPU smoke test)

```bash
pip install -r requirements.txt
python -I scripts/download_data.py --out data/primock57 --limit 3
python -I scripts/prep_data.py --src data/primock57 --out data/prepared_3min --limit 3 --max-seconds 180
python -I scripts/transcribe.py --data data/prepared_3min --out outputs/fw-base --model base
python -I scripts/evaluate.py --data data/prepared_3min --hyp outputs/fw-base --results results/fw-base
```
(`-I` keeps Python from importing anything from the data folder or the working directory.)

## Run on Colab (full: 57 consultations, large-v3)

Open `colab_full_run.ipynb` in Colab, choose a GPU runtime and run all cells. By default it saves to
`MyDrive/medasr` and resumes after a disconnect. That is about 26 h of audio in total (3 conditions x 8.6 h).
`large-v3-turbo` is the faster alternative.
If you edit the scripts, re-run `python -I scripts/make_colab_notebook.py`.

## Test-set results (47 consultations)

Run on an RTX 5080 Laptop GPU; setup, commands and all tables are in `docs/smoke-test-setup.md` (Chinese).
Eight ASR runs (Whisper large-v3, Parakeet TDT 0.6B v2, Granite Speech 4.1 2B, Qwen3-ASR-1.7B, Cohere Transcribe,
Canary-Qwen 2.5B; Whisper and Parakeet also with the shared chunk plan) were compared with paired bootstrap
over consultations on the mixed channel.

- **Qwen3-ASR-1.7B is the best.** Its corrected WER, medical-term error rate and clinical-negation loss are lower
  than every other run's, and none of the 95% intervals includes 0. It produced no repetition loops.
- **The other runs are close to each other within the error margin.** We do not rank them.
- Details: `results/test47/asr_selection.md`, `results/test47/bootstrap/pairwise.csv`, `results/test47/repeats/`.

Limitations:
- **Overlap.** Speech overlap remains the main mixed-channel failure for every model. Qwen3-ASR still deletes
  20% of the words inside doctor-patient overlaps.
- **One dataset.** All results come from PriMock57: simulated UK telehealth consultations.
- **Mixed channel only in the note grid.** The note-level grid (ASR source x generation model) uses the
  mixed channel only. Separated-channel notes need word timestamps to interleave the two channels into turns,
  and Qwen3-ASR does not produce them by default. That comparison is left out.

## CPU smoke-test results (initial sandbox, superseded by the test-set results above)

**Not run yet.** The sandbox this was built in cannot reach `huggingface.co` (blocked by its egress policy), so the
faster-whisper weights (`Systran/faster-whisper-*`) and the Parakeet weights could not be downloaded.
Everything up to and around the model has been run:

- download (3 consultations, sha256 verified) and prep (full length and 3-minute crops) ran on real data;
- the transcribe -> evaluate path was exercised with a **mock model** that echoes the reference with injected errors.
  It found the injected 4-word insertion and the deleted term (`diarrhea`). This only checks the code, so no ASR numbers come from it.

Prepared 3-minute subset (real reference statistics):

| consultation | cropped length | utterances | reference words (raw) |
|---|---|---|---|
| day1_consultation01 | 178.2 s | 35 | 564 |
| day1_consultation02 | 176.1 s | 37 | 542 |
| day1_consultation03 | 179.6 s | 44 | 523 |

Fill in after running the commands above (small model, small subset, so don't read much into it):

| consultations | model | condition | WER | term recall | s per audio-min |
|---|---|---|---|---|---|
| 3 x ~3 min | base (CPU int8) | doctor | – | – | – |
| 3 x ~3 min | base (CPU int8) | patient | – | – | – |
| 3 x ~3 min | base (CPU int8) | mixed | – | – | – |

## Untested
- Real faster-whisper inference (the code follows the faster-whisper 1.2 API; verified only with a mock).
- Parakeet / NeMo backend (not installed; the model is also on Hugging Face).
- The scispaCy path. Here, scispaCy failed to build on Python 3.13, and the `en_core_sci_sm` S3 URL is blocked.
  On Colab the optional cell may work. If it doesn't, the lexicon fallback is used automatically.

## License
- Code and documentation: MIT (`LICENSE`).
- Data: PriMock57 is CC BY 4.0 (see "Data: PriMock57" above); result files that quote its transcripts and
  clinician notes are derived from it and keep that attribution. Stress-test noise (DEMAND) and alarm sounds
  (Freesound, CC0) are not redistributed; sources and licences are in `docs/stress-test.md`.
- Note judging calls the Claude Code CLI (`claude -p`); reproducing it needs a Claude Code installation.
