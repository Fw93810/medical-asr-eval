# What the WER is made of (test set)

## s3_snr10-qwen3asr

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical |  |  | 0.07 (0%) |
| negation_discourse |  |  | 0.35 (2%) |
| number_duration |  |  | 0.27 (2%) |
| proper_or_drug |  |  | 0.23 (1%) |
| medical_term |  |  | 1.72 (11%) |
| backchannel |  |  | 3.73 (24%) |
| function |  |  | 7.66 (50%) |
| content |  |  | 1.29 (8%) |
| **total WER** | **15.31** |

| | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 1.79 |
| WER without normalisation artefacts | 13.53 |
| errors at uncertain reference: upper bound, not subtracted (points) | 3.71 |
- mixed: WER without backchannels 12.55, content-word WER 12.10, medical-term error rate 10.54, number/duration error rate 14.13

## s3_snr10-whisper

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical |  |  | 0.09 (0%) |
| negation_discourse |  |  | 0.44 (3%) |
| number_duration |  |  | 0.27 (2%) |
| proper_or_drug |  |  | 0.21 (1%) |
| medical_term |  |  | 1.81 (11%) |
| backchannel |  |  | 3.89 (23%) |
| function |  |  | 8.99 (53%) |
| content |  |  | 1.42 (8%) |
| **total WER** | **17.12** |

| | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 1.53 |
| WER without normalisation artefacts | 15.59 |
| errors at uncertain reference: upper bound, not subtracted (points) | 4.06 |
- mixed: WER without backchannels 14.30, content-word WER 12.47, medical-term error rate 11.23, number/duration error rate 13.41

