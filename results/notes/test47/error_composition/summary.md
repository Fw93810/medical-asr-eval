# What the note errors are made of (test set, 47 consultations)

Share of the clinician's facts that a note does not contain, by reason:

| source (vs baseline) | not in note | never said | conversation contradicts clinician | partly said | generator omission (shared) | specific to this source (lost / gained) | recall on stated facts |
|---|---|---|---|---|---|---|---|
| human | 31.8% | 7.7% | 2.3% | 6.1% | 15.6% | – | 78.8% |
| human_rejudge (vs human) | 32.0% | 7.7% | 2.3% | 6.2% | 15.1% | 0.5% (7 / 7) | 78.8% |
| human_plain (vs human) | 31.9% | 7.5% | 2.6% | 6.0% | 11.1% | 4.8% (67 / 64) | 78.5% |
| human_unlabelled_plain (vs human_plain) | 32.2% | 7.5% | 2.4% | 6.4% | 12.0% | 4.0% (56 / 54) | 78.3% |
| asr_mixed_plain (vs human_unlabelled_plain) | 31.2% | 7.2% | 1.7% | 5.9% | 10.7% | 5.8% (81 / 75) | 77.8% |
| asr_separated_plain (vs human_plain) | 32.8% | 7.6% | 2.3% | 5.9% | 11.5% | 5.5% (78 / 61) | 77.0% |
| asr_mixed (vs human) | 32.4% | 7.4% | 2.0% | 6.2% | 10.5% | 6.3% (89 / 72) | 77.2% |
| asr_separated (vs human) | 31.8% | 7.5% | 1.9% | 6.5% | 10.3% | 5.5% (78 / 75) | 78.6% |

Extra claims per note:

| source | contradicts clinician | added negatives | other additions |
|---|---|---|---|
| human | 1.17 | 2.77 | 6.89 |
| human_rejudge | 1.28 | 2.66 | 6.62 |
| human_plain | 1.23 | 2.74 | 6.83 |
| human_unlabelled_plain | 1.23 | 2.64 | 6.26 |
| asr_mixed_plain | 1.15 | 2.83 | 6.89 |
| asr_separated_plain | 1.19 | 2.85 | 6.77 |
| asr_mixed | 1.0 | 2.68 | 6.57 |
| asr_separated | 1.09 | 3.0 | 6.55 |
