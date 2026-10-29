# What the WER is made of (test set)

## s1_2x-qwen3asr

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical |  |  | 0.11 (1%) |
| negation_discourse |  |  | 0.43 (3%) |
| number_duration |  |  | 0.22 (1%) |
| proper_or_drug |  |  | 0.14 (1%) |
| medical_term |  |  | 1.39 (9%) |
| backchannel |  |  | 4.34 (27%) |
| function |  |  | 8.08 (50%) |
| content |  |  | 1.38 (9%) |
| **total WER** | **16.08** |

| | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 1.36 |
| WER without normalisation artefacts | 14.72 |
| errors at uncertain reference: upper bound, not subtracted (points) | 4.54 |
- mixed: WER without backchannels 12.72, content-word WER 10.73, medical-term error rate 8.83, number/duration error rate 13.19

## s1_2x-whisper

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical |  |  | 0.13 (1%) |
| negation_discourse |  |  | 0.60 (3%) |
| number_duration |  |  | 0.28 (1%) |
| proper_or_drug |  |  | 0.15 (1%) |
| medical_term |  |  | 1.64 (9%) |
| backchannel |  |  | 4.41 (23%) |
| function |  |  | 10.03 (53%) |
| content |  |  | 1.80 (9%) |
| **total WER** | **19.04** |

| | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 1.15 |
| WER without normalisation artefacts | 17.89 |
| errors at uncertain reference: upper bound, not subtracted (points) | 5.27 |
- mixed: WER without backchannels 15.88, content-word WER 12.87, medical-term error rate 10.68, number/duration error rate 15.32

