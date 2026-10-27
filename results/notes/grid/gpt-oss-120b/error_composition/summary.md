# What the note errors are made of (test set, 47 consultations)

Share of the clinician's facts that a note does not contain, by reason:

| source (vs baseline) | not in note | never said | conversation contradicts clinician | partly said | generator omission (shared) | specific to this source (lost / gained) | recall on stated facts |
|---|---|---|---|---|---|---|---|
| human | 23.0% | 5.2% | 3.0% | 4.0% | 10.8% | – | 85.3% |
| human_rejudge (vs human) | 25.6% | 9.4% | 1.8% | 4.7% | 9.8% | 0.0% (0 / 1) | 86.5% |
| human_plain (vs human) | 23.6% | 5.0% | 2.6% | 5.0% | 7.0% | 4.0% (29 / 27) | 84.9% |
| asr_mixed (vs human) | 25.2% | 5.0% | 2.3% | 4.7% | 7.4% | 5.8% (42 / 24) | 82.2% |
| asr_mixed_qwen3asr (vs human) | 22.2% | 4.8% | 2.2% | 4.5% | 7.3% | 3.3% (24 / 25) | 85.6% |

Extra claims per note:

| source | contradicts clinician | added negatives | other additions |
|---|---|---|---|
| human | 1.4 | 3.12 | 8.8 |
| human_rejudge | 1.4 | 3.0 | 9.3 |
| human_plain | 1.36 | 3.08 | 9.64 |
| asr_mixed | 1.6 | 3.52 | 8.72 |
| asr_mixed_qwen3asr | 1.48 | 3.48 | 9.0 |
