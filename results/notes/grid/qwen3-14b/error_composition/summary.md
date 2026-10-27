# What the note errors are made of (test set, 47 consultations)

Share of the clinician's facts that a note does not contain, by reason:

| source (vs baseline) | not in note | never said | conversation contradicts clinician | partly said | generator omission (shared) | specific to this source (lost / gained) | recall on stated facts |
|---|---|---|---|---|---|---|---|
| human | 30.9% | 5.5% | 2.5% | 6.2% | 16.7% | – | 77.6% |
| human_rejudge (vs human) | 34.3% | 9.8% | 1.1% | 7.9% | 14.8% | 0.7% (2 / 1) | 78.5% |
| human_plain (vs human) | 32.0% | 5.7% | 2.9% | 6.6% | 12.1% | 4.7% (34 / 33) | 77.4% |
| asr_mixed (vs human) | 32.8% | 5.8% | 2.3% | 6.8% | 11.2% | 6.8% (49 / 40) | 76.2% |
| asr_mixed_qwen3asr (vs human) | 32.4% | 5.5% | 1.9% | 5.7% | 13.4% | 5.9% (43 / 24) | 74.4% |

Extra claims per note:

| source | contradicts clinician | added negatives | other additions |
|---|---|---|---|
| human | 1.16 | 2.36 | 6.12 |
| human_rejudge | 1.0 | 2.4 | 6.5 |
| human_plain | 1.4 | 2.6 | 6.04 |
| asr_mixed | 1.36 | 2.56 | 5.76 |
| asr_mixed_qwen3asr | 1.44 | 2.76 | 5.52 |
