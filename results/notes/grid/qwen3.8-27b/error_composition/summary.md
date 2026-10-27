# What the note errors are made of (test set, 47 consultations)

Share of the clinician's facts that a note does not contain, by reason:

| source (vs baseline) | not in note | never said | conversation contradicts clinician | partly said | generator omission (shared) | specific to this source (lost / gained) | recall on stated facts |
|---|---|---|---|---|---|---|---|
| human | 20.1% | 5.7% | 2.8% | 4.4% | 7.3% | – | 89.7% |
| human_rejudge (vs human) | 21.3% | 9.8% | 1.8% | 5.4% | 4.3% | 0.0% (0 / 1) | 94.0% |
| human_plain (vs human) | 19.0% | 5.7% | 2.6% | 4.3% | 4.3% | 2.2% (16 / 22) | 90.8% |
| asr_mixed (vs human) | 22.2% | 5.4% | 2.6% | 4.3% | 5.0% | 5.0% (36 / 17) | 86.3% |
| asr_mixed_qwen3asr (vs human) | 20.3% | 5.5% | 1.9% | 4.7% | 5.0% | 3.2% (23 / 17) | 88.8% |

Extra claims per note:

| source | contradicts clinician | added negatives | other additions |
|---|---|---|---|
| human | 1.2 | 2.56 | 9.08 |
| human_rejudge | 0.8 | 2.2 | 8.7 |
| human_plain | 1.36 | 2.88 | 8.4 |
| asr_mixed | 1.52 | 2.8 | 9.16 |
| asr_mixed_qwen3asr | 1.48 | 3.12 | 8.64 |
