# What the WER is made of (test set)

## clean-qwen3asr

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical |  |  | 0.04 (0%) |
| negation_discourse |  |  | 0.25 (2%) |
| number_duration |  |  | 0.18 (2%) |
| proper_or_drug |  |  | 0.16 (1%) |
| medical_term |  |  | 1.03 (9%) |
| backchannel |  |  | 3.55 (32%) |
| function |  |  | 5.06 (46%) |
| content |  |  | 0.73 (7%) |
| **total WER** | **10.99** |

| | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 2.29 |
| WER without normalisation artefacts | 8.70 |
| errors at uncertain reference: upper bound, not subtracted (points) | 3.17 |
- mixed: WER without backchannels 8.14, content-word WER 7.40, medical-term error rate 5.57, number/duration error rate 7.88

## clean-whisper

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical |  |  | 0.05 (0%) |
| negation_discourse |  |  | 0.31 (3%) |
| number_duration |  |  | 0.20 (2%) |
| proper_or_drug |  |  | 0.17 (1%) |
| medical_term |  |  | 1.18 (9%) |
| backchannel |  |  | 3.64 (29%) |
| function |  |  | 6.06 (48%) |
| content |  |  | 0.92 (7%) |
| **total WER** | **12.52** |

| | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 2.2 |
| WER without normalisation artefacts | 10.32 |
| errors at uncertain reference: upper bound, not subtracted (points) | 3.45 |
- mixed: WER without backchannels 9.68, content-word WER 8.38, medical-term error rate 6.83, number/duration error rate 8.51

