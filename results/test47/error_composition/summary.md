# What the WER is made of (test set)

## test47-parakeet-local

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical | 0.03 (0%) | 0.09 (1%) | 0.07 (1%) |
| negation_discourse | 0.10 (1%) | 1.10 (8%) | 0.29 (2%) |
| number_duration | 0.10 (1%) | 0.25 (2%) | 0.15 (1%) |
| proper_or_drug | 0.18 (2%) | 0.28 (2%) | 0.21 (2%) |
| medical_term | 0.99 (9%) | 1.56 (11%) | 1.12 (9%) |
| backchannel | 3.96 (35%) | 2.23 (15%) | 3.58 (28%) |
| function | 5.31 (47%) | 7.73 (53%) | 6.62 (51%) |
| content | 0.70 (6%) | 1.23 (8%) | 0.86 (7%) |
| **total WER** | **11.38** | **14.48** | **12.91** |

| | doctor | patient | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 3.31 | 1.2 | 2.19 |
| WER without normalisation artefacts | 8.07 | 13.28 | 10.72 |
| errors at uncertain reference: upper bound, not subtracted (points) | 2.79 | 4.39 | 3.49 |
- doctor: WER without backchannels 8.11, content-word WER 6.50, medical-term error rate 4.97, number/duration error rate 5.20
- patient: WER without backchannels 13.41, content-word WER 12.42, medical-term error rate 10.11, number/duration error rate 8.30
- mixed: WER without backchannels 10.14, content-word WER 8.07, medical-term error rate 6.31, number/duration error rate 7.25

## test47-vad-nocond

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical | 0.03 (0%) | 0.08 (1%) | 0.05 (0%) |
| negation_discourse | 0.11 (1%) | 0.59 (5%) | 0.31 (3%) |
| number_duration | 0.11 (1%) | 0.31 (2%) | 0.20 (2%) |
| proper_or_drug | 0.15 (1%) | 0.21 (2%) | 0.17 (1%) |
| medical_term | 0.91 (8%) | 1.42 (11%) | 1.18 (9%) |
| backchannel | 4.06 (37%) | 2.31 (18%) | 3.64 (29%) |
| function | 4.93 (45%) | 6.93 (53%) | 6.06 (48%) |
| content | 0.65 (6%) | 1.12 (9%) | 0.92 (7%) |
| **total WER** | **10.96** | **12.97** | **12.52** |

| | doctor | patient | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 3.11 | 1.18 | 2.2 |
| WER without normalisation artefacts | 7.85 | 11.79 | 10.32 |
| errors at uncertain reference: upper bound, not subtracted (points) | 2.74 | 4.19 | 3.45 |
- doctor: WER without backchannels 7.55, content-word WER 6.08, medical-term error rate 4.66, number/duration error rate 5.76
- patient: WER without backchannels 11.64, content-word WER 11.59, medical-term error rate 9.52, number/duration error rate 9.89
- mixed: WER without backchannels 9.68, content-word WER 8.38, medical-term error rate 6.83, number/duration error rate 8.51

