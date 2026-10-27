# What the WER is made of (test set)

## full10-novad-nocond

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical | 0.07 (0%) | 0.15 (1%) | 0.11 (1%) |
| negation_discourse | 0.18 (1%) | 0.89 (5%) | 0.39 (2%) |
| number_duration | 0.33 (2%) | 0.23 (1%) | 0.17 (1%) |
| proper_or_drug | 0.15 (1%) | 0.14 (1%) | 0.13 (1%) |
| medical_term | 1.34 (8%) | 1.45 (8%) | 1.35 (8%) |
| backchannel | 4.81 (29%) | 2.20 (13%) | 4.13 (24%) |
| function | 8.40 (50%) | 10.92 (63%) | 9.18 (54%) |
| content | 1.43 (9%) | 1.48 (8%) | 1.45 (9%) |
| **total WER** | **16.71** | **17.45** | **16.90** |

| | doctor | patient | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 3.1 | 0.89 | 1.91 |
| WER without normalisation artefacts | 13.61 | 16.56 | 14.99 |
| errors at uncertain reference: upper bound, not subtracted (points) | 4.79 | 5.13 | 4.94 |
- doctor: WER without backchannels 13.33, content-word WER 10.27, medical-term error rate 6.52, number/duration error rate 13.43
- patient: WER without backchannels 16.44, content-word WER 12.48, medical-term error rate 10.80, number/duration error rate 6.93
- mixed: WER without backchannels 13.92, content-word WER 10.60, medical-term error rate 8.42, number/duration error rate 9.36

## full10-vad-nocond

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical | 0.09 (1%) | 0.13 (1%) | 0.10 (1%) |
| negation_discourse | 0.23 (1%) | 0.76 (5%) | 0.44 (3%) |
| number_duration | 0.19 (1%) | 0.18 (1%) | 0.21 (1%) |
| proper_or_drug | 0.14 (1%) | 0.14 (1%) | 0.16 (1%) |
| medical_term | 1.22 (7%) | 1.37 (9%) | 1.39 (8%) |
| backchannel | 4.71 (29%) | 2.07 (14%) | 4.20 (24%) |
| function | 8.52 (52%) | 8.58 (59%) | 9.22 (54%) |
| content | 1.35 (8%) | 1.38 (9%) | 1.43 (8%) |
| **total WER** | **16.45** | **14.61** | **17.15** |

| | doctor | patient | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 3.35 | 0.83 | 1.9 |
| WER without normalisation artefacts | 13.10 | 13.77 | 15.25 |
| errors at uncertain reference: upper bound, not subtracted (points) | 4.54 | 4.35 | 4.89 |
- doctor: WER without backchannels 13.02, content-word WER 9.13, medical-term error rate 6.39, number/duration error rate 10.45
- patient: WER without backchannels 13.48, content-word WER 11.73, medical-term error rate 10.00, number/duration error rate 5.94
- mixed: WER without backchannels 14.14, content-word WER 10.83, medical-term error rate 8.54, number/duration error rate 10.64

## full10-vad-nocond-pad1500

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical | 0.09 (1%) | 0.10 (1%) | 0.09 (1%) |
| negation_discourse | 0.16 (1%) | 0.75 (5%) | 0.41 (2%) |
| number_duration | 0.21 (1%) | 0.23 (1%) | 0.22 (1%) |
| proper_or_drug | 0.12 (1%) | 0.08 (1%) | 0.13 (1%) |
| medical_term | 1.31 (7%) | 1.41 (9%) | 1.33 (8%) |
| backchannel | 4.83 (27%) | 2.10 (13%) | 4.18 (25%) |
| function | 9.42 (53%) | 10.27 (63%) | 8.92 (53%) |
| content | 1.48 (8%) | 1.44 (9%) | 1.45 (9%) |
| **total WER** | **17.62** | **16.37** | **16.73** |

| | doctor | patient | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 3.23 | 0.83 | 1.91 |
| WER without normalisation artefacts | 14.39 | 15.54 | 14.82 |
| errors at uncertain reference: upper bound, not subtracted (points) | 4.66 | 4.58 | 4.84 |
- doctor: WER without backchannels 14.17, content-word WER 9.86, medical-term error rate 6.89, number/duration error rate 12.69
- patient: WER without backchannels 15.36, content-word WER 12.63, medical-term error rate 10.34, number/duration error rate 7.92
- mixed: WER without backchannels 13.71, content-word WER 10.46, medical-term error rate 8.26, number/duration error rate 10.64

## full10-vad-nocond-pad800

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical | 0.06 (0%) | 0.13 (1%) | 0.08 (0%) |
| negation_discourse | 0.19 (1%) | 0.62 (4%) | 0.42 (2%) |
| number_duration | 0.23 (1%) | 0.17 (1%) | 0.21 (1%) |
| proper_or_drug | 0.14 (1%) | 0.10 (1%) | 0.15 (1%) |
| medical_term | 1.17 (7%) | 1.39 (10%) | 1.43 (8%) |
| backchannel | 4.81 (30%) | 1.92 (13%) | 4.14 (24%) |
| function | 8.32 (51%) | 8.76 (61%) | 9.06 (53%) |
| content | 1.28 (8%) | 1.30 (9%) | 1.54 (9%) |
| **total WER** | **16.20** | **14.38** | **17.03** |

| | doctor | patient | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 3.31 | 0.97 | 1.95 |
| WER without normalisation artefacts | 12.89 | 13.41 | 15.08 |
| errors at uncertain reference: upper bound, not subtracted (points) | 4.26 | 4.34 | 4.83 |
- doctor: WER without backchannels 12.69, content-word WER 8.95, medical-term error rate 6.15, number/duration error rate 12.69
- patient: WER without backchannels 13.41, content-word WER 11.52, medical-term error rate 9.89, number/duration error rate 3.96
- mixed: WER without backchannels 14.09, content-word WER 11.05, medical-term error rate 8.95, number/duration error rate 11.06

