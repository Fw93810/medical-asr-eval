# What the WER is made of (test set)

## s3_snr20-qwen3asr

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical |  |  | 0.04 (0%) |
| negation_discourse |  |  | 0.29 (2%) |
| number_duration |  |  | 0.18 (1%) |
| proper_or_drug |  |  | 0.18 (2%) |
| medical_term |  |  | 1.20 (10%) |
| backchannel |  |  | 3.62 (30%) |
| function |  |  | 5.70 (47%) |
| content |  |  | 0.91 (8%) |
| **total WER** | **12.13** |

| | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 2.16 |
| WER without normalisation artefacts | 9.97 |
| errors at uncertain reference: upper bound, not subtracted (points) | 3.38 |
- mixed: WER without backchannels 9.29, content-word WER 8.65, medical-term error rate 6.77, number/duration error rate 8.06

## s3_snr20-whisper

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical |  |  | 0.06 (0%) |
| negation_discourse |  |  | 0.37 (3%) |
| number_duration |  |  | 0.24 (2%) |
| proper_or_drug |  |  | 0.17 (1%) |
| medical_term |  |  | 1.37 (10%) |
| backchannel |  |  | 3.76 (26%) |
| function |  |  | 7.17 (50%) |
| content |  |  | 1.09 (8%) |
| **total WER** | **14.24** |

| | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 1.87 |
| WER without normalisation artefacts | 12.37 |
| errors at uncertain reference: upper bound, not subtracted (points) | 3.76 |
- mixed: WER without backchannels 11.38, content-word WER 9.77, medical-term error rate 8.41, number/duration error rate 11.50

