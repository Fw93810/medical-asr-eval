# What the WER is made of (test set)

## s1_3x-qwen3asr

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical |  |  | 0.12 (1%) |
| negation_discourse |  |  | 0.64 (3%) |
| number_duration |  |  | 0.26 (1%) |
| proper_or_drug |  |  | 0.13 (1%) |
| medical_term |  |  | 2.13 (10%) |
| backchannel |  |  | 4.69 (23%) |
| function |  |  | 10.67 (52%) |
| content |  |  | 1.98 (10%) |
| **total WER** | **20.63** |

| | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 0.92 |
| WER without normalisation artefacts | 19.70 |
| errors at uncertain reference: upper bound, not subtracted (points) | 5.44 |
- mixed: WER without backchannels 17.31, content-word WER 14.92, medical-term error rate 14.07, number/duration error rate 17.45

## s1_3x-whisper

WER points by word class (share of all errors in brackets):

| word class | doctor | patient | mixed |
|---|---|---|---|
| negation_clinical |  |  | 0.17 (1%) |
| negation_discourse |  |  | 0.73 (3%) |
| number_duration |  |  | 0.30 (1%) |
| proper_or_drug |  |  | 0.15 (1%) |
| medical_term |  |  | 2.35 (10%) |
| backchannel |  |  | 4.87 (21%) |
| function |  |  | 12.58 (54%) |
| content |  |  | 2.29 (10%) |
| **total WER** | **23.44** |

| | mixed |
|---|---|---|---|
| normalisation artefacts (points) | 0.89 |
| WER without normalisation artefacts | 22.55 |
| errors at uncertain reference: upper bound, not subtracted (points) | 5.83 |
- mixed: WER without backchannels 20.12, content-word WER 16.69, medical-term error rate 15.48, number/duration error rate 19.57

