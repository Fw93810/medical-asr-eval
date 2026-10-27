# What the WER is made of (test set)

## s1_1x-qwen3asr

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical |  |  | 0.06 (0%) |
| negation_discourse |  |  | 0.26 (2%) |
| number_duration |  |  | 0.16 (1%) |
| proper_or_drug |  |  | 0.16 (1%) |
| medical_term |  |  | 1.14 (8%) |
| backchannel |  |  | 4.03 (29%) |
| function |  |  | 7.10 (50%) |
| content |  |  | 1.19 (8%) |
| **total WER** | **14.12** |

| | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 2.04 |
| WER without normalisation artefacts | 12.08 |
| errors at uncertain reference: upper bound, not subtracted (points) | 4.43 |
- mixed: WER without backchannels 11.04, content-word WER 9.12, medical-term error rate 6.53, number/duration error rate 8.09

## s1_1x-whisper

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical |  |  | 0.09 (1%) |
| negation_discourse |  |  | 0.34 (2%) |
| number_duration |  |  | 0.20 (1%) |
| proper_or_drug |  |  | 0.15 (1%) |
| medical_term |  |  | 1.40 (8%) |
| backchannel |  |  | 4.17 (25%) |
| function |  |  | 8.84 (53%) |
| content |  |  | 1.38 (8%) |
| **total WER** | **16.57** |

| | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 1.96 |
| WER without normalisation artefacts | 14.61 |
| errors at uncertain reference: upper bound, not subtracted (points) | 4.89 |
- mixed: WER without backchannels 13.49, content-word WER 10.59, medical-term error rate 8.46, number/duration error rate 9.79

