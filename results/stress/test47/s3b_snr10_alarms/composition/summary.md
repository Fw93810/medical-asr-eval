# What the WER is made of (test set)

## s3b_snr10_alarms-qwen3asr

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical |  |  | 0.07 (0%) |
| negation_discourse |  |  | 0.34 (2%) |
| number_duration |  |  | 0.27 (2%) |
| proper_or_drug |  |  | 0.22 (1%) |
| medical_term |  |  | 1.76 (11%) |
| backchannel |  |  | 3.79 (24%) |
| function |  |  | 7.93 (50%) |
| content |  |  | 1.33 (8%) |
| **total WER** | **15.72** |

| | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 1.73 |
| WER without normalisation artefacts | 13.99 |
| errors at uncertain reference: upper bound, not subtracted (points) | 3.76 |
- mixed: WER without backchannels 12.92, content-word WER 12.37, medical-term error rate 10.96, number/duration error rate 14.40

## s3b_snr10_alarms-whisper

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical |  |  | 0.10 (1%) |
| negation_discourse |  |  | 0.45 (3%) |
| number_duration |  |  | 0.26 (1%) |
| proper_or_drug |  |  | 0.23 (1%) |
| medical_term |  |  | 1.91 (11%) |
| backchannel |  |  | 3.88 (22%) |
| function |  |  | 9.42 (53%) |
| content |  |  | 1.46 (8%) |
| **total WER** | **17.71** |

| | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 1.55 |
| WER without normalisation artefacts | 16.16 |
| errors at uncertain reference: upper bound, not subtracted (points) | 4.13 |
- mixed: WER without backchannels 14.97, content-word WER 13.00, medical-term error rate 12.00, number/duration error rate 12.86

