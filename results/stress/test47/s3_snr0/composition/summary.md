# What the WER is made of (test set)

## s3_snr0-qwen3asr

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical |  |  | 0.20 (1%) |
| negation_discourse |  |  | 0.68 (2%) |
| number_duration |  |  | 0.55 (2%) |
| proper_or_drug |  |  | 0.42 (1%) |
| medical_term |  |  | 4.86 (14%) |
| backchannel |  |  | 4.41 (13%) |
| function |  |  | 18.83 (56%) |
| content |  |  | 3.97 (12%) |
| **total WER** | **33.92** |

| | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 0.8 |
| WER without normalisation artefacts | 33.12 |
| errors at uncertain reference: upper bound, not subtracted (points) | 5.27 |
- mixed: WER without backchannels 31.73, content-word WER 32.48, medical-term error rate 32.66, number/duration error rate 32.43

## s3_snr0-whisper

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical |  |  | 0.21 (1%) |
| negation_discourse |  |  | 0.68 (2%) |
| number_duration |  |  | 0.54 (2%) |
| proper_or_drug |  |  | 0.38 (1%) |
| medical_term |  |  | 4.40 (14%) |
| backchannel |  |  | 4.53 (14%) |
| function |  |  | 17.96 (56%) |
| content |  |  | 3.64 (11%) |
| **total WER** | **32.34** |

| | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 0.78 |
| WER without normalisation artefacts | 31.56 |
| errors at uncertain reference: upper bound, not subtracted (points) | 5.46 |
- mixed: WER without backchannels 30.04, content-word WER 29.70, medical-term error rate 28.74, number/duration error rate 30.53

