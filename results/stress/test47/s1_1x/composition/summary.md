# What the WER is made of (test set)

## s1_1x-qwen3asr

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical |  |  | 0.03 (0%) |
| negation_discourse |  |  | 0.23 (2%) |
| number_duration |  |  | 0.18 (2%) |
| proper_or_drug |  |  | 0.15 (1%) |
| medical_term |  |  | 0.99 (9%) |
| backchannel |  |  | 3.51 (33%) |
| function |  |  | 4.96 (46%) |
| content |  |  | 0.70 (6%) |
| **total WER** | **10.75** |

| | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 2.33 |
| WER without normalisation artefacts | 8.42 |
| errors at uncertain reference: upper bound, not subtracted (points) | 3.13 |
- mixed: WER without backchannels 7.92, content-word WER 7.10, medical-term error rate 5.41, number/duration error rate 7.34

## s1_1x-whisper

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical |  |  | 0.05 (0%) |
| negation_discourse |  |  | 0.30 (2%) |
| number_duration |  |  | 0.19 (2%) |
| proper_or_drug |  |  | 0.19 (2%) |
| medical_term |  |  | 1.11 (9%) |
| backchannel |  |  | 3.58 (29%) |
| function |  |  | 5.97 (49%) |
| content |  |  | 0.88 (7%) |
| **total WER** | **12.26** |

| | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 2.24 |
| WER without normalisation artefacts | 10.02 |
| errors at uncertain reference: upper bound, not subtracted (points) | 3.36 |
- mixed: WER without backchannels 9.46, content-word WER 8.16, medical-term error rate 6.51, number/duration error rate 8.06

