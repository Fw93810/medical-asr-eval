# What the WER is made of (test set)

## s1_3x-qwen3asr

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical |  |  | 0.05 (0%) |
| negation_discourse |  |  | 0.35 (3%) |
| number_duration |  |  | 0.21 (2%) |
| proper_or_drug |  |  | 0.17 (1%) |
| medical_term |  |  | 1.31 (10%) |
| backchannel |  |  | 3.83 (29%) |
| function |  |  | 6.13 (47%) |
| content |  |  | 1.02 (8%) |
| **total WER** | **13.06** |

| | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 1.67 |
| WER without normalisation artefacts | 11.40 |
| errors at uncertain reference: upper bound, not subtracted (points) | 3.35 |
- mixed: WER without backchannels 10.05, content-word WER 9.27, medical-term error rate 8.07, number/duration error rate 10.51

## s1_3x-whisper

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical |  |  | 0.07 (0%) |
| negation_discourse |  |  | 0.45 (3%) |
| number_duration |  |  | 0.24 (2%) |
| proper_or_drug |  |  | 0.17 (1%) |
| medical_term |  |  | 1.59 (11%) |
| backchannel |  |  | 4.00 (27%) |
| function |  |  | 7.22 (48%) |
| content |  |  | 1.21 (8%) |
| **total WER** | **14.96** |

| | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 1.49 |
| WER without normalisation artefacts | 13.47 |
| errors at uncertain reference: upper bound, not subtracted (points) | 3.78 |
- mixed: WER without backchannels 11.88, content-word WER 10.86, medical-term error rate 10.00, number/duration error rate 12.32

