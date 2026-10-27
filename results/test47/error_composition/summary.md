# What the WER is made of (test set)

## test47-canary-qwen-2.5b

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical | 0.02 (0%) | 0.07 (1%) | 0.04 (0%) |
| negation_discourse | 0.11 (1%) | 0.47 (4%) | 0.30 (2%) |
| number_duration | 0.10 (1%) | 0.30 (2%) | 0.19 (2%) |
| proper_or_drug | 0.14 (1%) | 0.20 (2%) | 0.16 (1%) |
| medical_term | 0.86 (8%) | 1.36 (11%) | 1.14 (9%) |
| backchannel | 4.04 (39%) | 2.19 (18%) | 3.62 (30%) |
| function | 4.52 (43%) | 6.28 (52%) | 5.67 (47%) |
| content | 0.63 (6%) | 1.13 (9%) | 0.89 (7%) |
| **total WER** | **10.42** | **11.99** | **12.01** |

| | doctor | patient | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 3.34 | 1.23 | 2.29 |
| WER without normalisation artefacts | 7.08 | 10.76 | 9.72 |
| errors at uncertain reference: upper bound, not subtracted (points) | 2.7 | 4.19 | 3.5 |
- doctor: WER without backchannels 6.99, content-word WER 5.68, medical-term error rate 4.28, number/duration error rate 4.65
- patient: WER without backchannels 10.76, content-word WER 11.20, medical-term error rate 8.69, number/duration error rate 7.77
- mixed: WER without backchannels 9.17, content-word WER 8.10, medical-term error rate 6.24, number/duration error rate 7.97

## test47-cohere-transcribe

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical | 0.04 (0%) | 0.15 (1%) | 0.08 (1%) |
| negation_discourse | 0.11 (1%) | 0.61 (4%) | 0.31 (2%) |
| number_duration | 0.13 (1%) | 0.26 (2%) | 0.18 (1%) |
| proper_or_drug | 0.16 (1%) | 0.23 (2%) | 0.18 (1%) |
| medical_term | 0.83 (7%) | 1.40 (9%) | 1.29 (9%) |
| backchannel | 3.98 (35%) | 2.51 (17%) | 3.60 (26%) |
| function | 5.64 (49%) | 8.80 (58%) | 7.30 (53%) |
| content | 0.60 (5%) | 1.14 (8%) | 0.80 (6%) |
| **total WER** | **11.49** | **15.10** | **13.74** |

| | doctor | patient | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 3.2 | 1.1 | 2.22 |
| WER without normalisation artefacts | 8.28 | 14.01 | 11.52 |
| errors at uncertain reference: upper bound, not subtracted (points) | 2.71 | 4.4 | 3.54 |
- doctor: WER without backchannels 8.20, content-word WER 5.72, medical-term error rate 4.21, number/duration error rate 5.58
- patient: WER without backchannels 13.76, content-word WER 11.44, medical-term error rate 8.48, number/duration error rate 9.19
- mixed: WER without backchannels 11.03, content-word WER 8.68, medical-term error rate 6.21, number/duration error rate 7.52

## test47-granite-4.1-2b

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical | 0.05 (0%) | 0.14 (1%) | 0.07 (0%) |
| negation_discourse | 0.10 (1%) | 2.07 (9%) | 0.44 (3%) |
| number_duration | 0.11 (1%) | 0.29 (1%) | 0.22 (1%) |
| proper_or_drug | 0.15 (1%) | 0.26 (1%) | 0.18 (1%) |
| medical_term | 0.94 (8%) | 1.99 (8%) | 1.26 (9%) |
| backchannel | 4.07 (34%) | 6.16 (26%) | 3.80 (26%) |
| function | 5.93 (49%) | 11.28 (48%) | 7.76 (53%) |
| content | 0.74 (6%) | 1.31 (6%) | 0.99 (7%) |
| **total WER** | **12.09** | **23.50** | **14.72** |

| | doctor | patient | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 3.01 | 1.09 | 1.99 |
| WER without normalisation artefacts | 9.08 | 22.41 | 12.73 |
| errors at uncertain reference: upper bound, not subtracted (points) | 2.79 | 6.58 | 3.76 |
- doctor: WER without backchannels 8.74, content-word WER 6.28, medical-term error rate 5.12, number/duration error rate 5.58
- patient: WER without backchannels 18.78, content-word WER 14.30, medical-term error rate 11.64, number/duration error rate 10.60
- mixed: WER without backchannels 11.85, content-word WER 9.04, medical-term error rate 7.79, number/duration error rate 9.60

## test47-parakeet-chunked

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical | 0.04 (0%) | 0.07 (1%) | 0.05 (0%) |
| negation_discourse | 0.09 (1%) | 0.47 (4%) | 0.27 (2%) |
| number_duration | 0.08 (1%) | 0.29 (2%) | 0.16 (1%) |
| proper_or_drug | 0.18 (2%) | 0.25 (2%) | 0.21 (2%) |
| medical_term | 0.96 (9%) | 1.54 (12%) | 1.19 (10%) |
| backchannel | 4.01 (38%) | 2.22 (18%) | 3.56 (29%) |
| function | 4.48 (43%) | 6.48 (52%) | 5.93 (48%) |
| content | 0.70 (7%) | 1.26 (10%) | 0.90 (7%) |
| **total WER** | **10.55** | **12.58** | **12.26** |

| | doctor | patient | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 3.26 | 1.16 | 2.27 |
| WER without normalisation artefacts | 7.29 | 11.42 | 9.99 |
| errors at uncertain reference: upper bound, not subtracted (points) | 2.74 | 4.6 | 3.49 |
- doctor: WER without backchannels 7.19, content-word WER 6.38, medical-term error rate 4.48, number/duration error rate 4.46
- patient: WER without backchannels 11.34, content-word WER 12.30, medical-term error rate 8.88, number/duration error rate 8.66
- mixed: WER without backchannels 9.50, content-word WER 8.51, medical-term error rate 6.47, number/duration error rate 7.43

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

## test47-qwen3-asr-1.7b

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical | 0.02 (0%) | 0.04 (0%) | 0.04 (0%) |
| negation_discourse | 0.08 (1%) | 0.42 (4%) | 0.25 (2%) |
| number_duration | 0.09 (1%) | 0.25 (2%) | 0.18 (2%) |
| proper_or_drug | 0.13 (1%) | 0.19 (2%) | 0.16 (1%) |
| medical_term | 0.81 (8%) | 1.23 (11%) | 1.03 (9%) |
| backchannel | 3.99 (42%) | 2.22 (21%) | 3.55 (32%) |
| function | 3.87 (41%) | 5.47 (51%) | 5.06 (46%) |
| content | 0.52 (5%) | 0.93 (9%) | 0.73 (7%) |
| **total WER** | **9.52** | **10.74** | **10.99** |

| | doctor | patient | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 3.32 | 1.35 | 2.29 |
| WER without normalisation artefacts | 6.20 | 9.40 | 8.70 |
| errors at uncertain reference: upper bound, not subtracted (points) | 2.3 | 3.91 | 3.17 |
- doctor: WER without backchannels 6.12, content-word WER 5.23, medical-term error rate 3.84, number/duration error rate 3.90
- patient: WER without backchannels 9.33, content-word WER 9.94, medical-term error rate 6.91, number/duration error rate 7.60
- mixed: WER without backchannels 8.14, content-word WER 7.40, medical-term error rate 5.57, number/duration error rate 7.88

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

## test47-whisper-chunked

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical | 0.03 (0%) | 0.12 (1%) | 0.06 (0%) |
| negation_discourse | 0.11 (1%) | 0.58 (4%) | 0.33 (3%) |
| number_duration | 0.11 (1%) | 0.33 (2%) | 0.19 (1%) |
| proper_or_drug | 0.15 (1%) | 0.24 (2%) | 0.18 (1%) |
| medical_term | 0.91 (8%) | 1.41 (10%) | 1.15 (9%) |
| backchannel | 4.03 (36%) | 2.44 (17%) | 3.66 (28%) |
| function | 5.21 (46%) | 8.28 (57%) | 6.51 (50%) |
| content | 0.67 (6%) | 1.18 (8%) | 0.92 (7%) |
| **total WER** | **11.21** | **14.59** | **13.00** |

| | doctor | patient | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 3.15 | 1.22 | 2.15 |
| WER without normalisation artefacts | 8.07 | 13.37 | 10.85 |
| errors at uncertain reference: upper bound, not subtracted (points) | 2.74 | 4.51 | 3.45 |
- doctor: WER without backchannels 7.88, content-word WER 6.07, medical-term error rate 4.56, number/duration error rate 5.20
- patient: WER without backchannels 13.26, content-word WER 12.02, medical-term error rate 8.94, number/duration error rate 10.42
- mixed: WER without backchannels 10.19, content-word WER 8.34, medical-term error rate 6.62, number/duration error rate 8.61

