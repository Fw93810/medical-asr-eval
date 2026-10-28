# What the WER is made of (test set)

## s1_2x-qwen3asr

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical |  |  | 0.03 (0%) |
| negation_discourse |  |  | 0.30 (3%) |
| number_duration |  |  | 0.18 (2%) |
| proper_or_drug |  |  | 0.16 (1%) |
| medical_term |  |  | 1.06 (9%) |
| backchannel |  |  | 3.69 (32%) |
| function |  |  | 5.30 (46%) |
| content |  |  | 0.81 (7%) |
| **total WER** | **11.53** |

| | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 2.12 |
| WER without normalisation artefacts | 9.40 |
| errors at uncertain reference: upper bound, not subtracted (points) | 3.2 |
- mixed: WER without backchannels 8.55, content-word WER 7.73, medical-term error rate 6.05, number/duration error rate 8.33

## s1_2x-whisper

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical |  |  | 0.06 (0%) |
| negation_discourse |  |  | 0.38 (3%) |
| number_duration |  |  | 0.20 (2%) |
| proper_or_drug |  |  | 0.17 (1%) |
| medical_term |  |  | 1.24 (9%) |
| backchannel |  |  | 3.79 (29%) |
| function |  |  | 6.35 (48%) |
| content |  |  | 1.03 (8%) |
| **total WER** | **13.22** |

| | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 1.94 |
| WER without normalisation artefacts | 11.28 |
| errors at uncertain reference: upper bound, not subtracted (points) | 3.57 |
- mixed: WER without backchannels 10.25, content-word WER 9.06, medical-term error rate 7.49, number/duration error rate 9.60

