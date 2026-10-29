# What the WER is made of (test set)

## s3_snr5-qwen3asr

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical |  |  | 0.10 (0%) |
| negation_discourse |  |  | 0.43 (2%) |
| number_duration |  |  | 0.33 (2%) |
| proper_or_drug |  |  | 0.26 (1%) |
| medical_term |  |  | 2.53 (12%) |
| backchannel |  |  | 3.95 (19%) |
| function |  |  | 10.82 (53%) |
| content |  |  | 1.99 (10%) |
| **total WER** | **20.41** |

| | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 1.38 |
| WER without normalisation artefacts | 19.03 |
| errors at uncertain reference: upper bound, not subtracted (points) | 4.12 |
- mixed: WER without backchannels 17.77, content-word WER 17.38, medical-term error rate 16.32, number/duration error rate 18.03

## s3_snr5-whisper

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical |  |  | 0.14 (1%) |
| negation_discourse |  |  | 0.55 (3%) |
| number_duration |  |  | 0.31 (1%) |
| proper_or_drug |  |  | 0.28 (1%) |
| medical_term |  |  | 2.60 (12%) |
| backchannel |  |  | 4.11 (19%) |
| function |  |  | 11.68 (54%) |
| content |  |  | 1.98 (9%) |
| **total WER** | **21.65** |

| | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 1.25 |
| WER without normalisation artefacts | 20.40 |
| errors at uncertain reference: upper bound, not subtracted (points) | 4.57 |
- mixed: WER without backchannels 18.97, content-word WER 17.41, medical-term error rate 16.37, number/duration error rate 15.94

