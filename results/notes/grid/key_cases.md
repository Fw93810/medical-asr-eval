# Key cases

**Source**: test set, mixed channel; times are the start of that utterance in the human transcript.

**Links**: each link opens the viewer page at that time. Start the local server first, from `D:\medical-asr-eval`:

```
python -I -m http.server 8765 --bind 127.0.0.1
```

then open `http://127.0.0.1:8765/results/viewer-test47/`.

**How notes are referred to**:

- A note is named "generation model × transcript source", e.g. 27B × Whisper is the note Qwen3.8-27B wrote from the Whisper transcript.
- Note texts are in `outputs/notes-grid/notes/<model>/<consultation>/<source>.json`.
- Only the 25 grid consultations have notes; consultations outside the grid (marked "not in grid") can only be examined at the ASR level.

## A. Negation flips: the ASR dropped a negation

| # | Consultation · time | Original (human transcript) | Whisper large-v3 | Qwen3-ASR-1.7B | Consequence in the notes |
|---|---|---|---|---|---|
| A1 | [day3_consultation03 · 280.6 s](../../viewer-test47/index.html#id=day3_consultation03&cond=mixed&t=278) patient | "I **don't** really have problems when going to the toilet, it's just painless." | "I would say I **really have problems** when going to the toilet it's just less so" | "I **don't** really have problems when going to the toilet. It's just been less." | **27B × Whisper** wrote "difficulty with bowel movements (described as 'less so' frequency)", and the judge marked the clinician's fact "Bowels normal" as **contradicted**. 27B × human and 27B × Qwen3-ASR both describe normal bowels ("No diarrhea, constipation…"). |
| A2 | [day4_consultation08 · 322.5 s](../../viewer-test47/index.html#id=day4_consultation08&cond=mixed&t=318) patient | "Um, I **haven't** noticed anything like that, specifically, no." | "I noticed anything like that specifically" | "I **haven't** noticed anything like that specifically." | **Rescued by the doctor's restatement**: the doctor immediately says "so you're saying you have **not** noticed morning erections", and every note that mentions it is correct. Restating an answer is natural redundancy against ASR negation errors. |
| A3 | [day3_consultation07 · 236.6 s](../../viewer-test47/index.html#id=day3_consultation07&cond=mixed&t=236) (not in grid) doctor | "There's no temperature, no joint pains, yeah? **No fever?**" | "…no joint pains yeah **you don't know**" | "…no joint pains. Yeah. No joint pains. **No.**" | Whisper turned "No fever?" into "you don't know", losing both the negation and the question. Not in the grid, so no notes. |

## B. Meaning flips

| # | Consultation · time | Original (human transcript) | Whisper large-v3 | Qwen3-ASR-1.7B | Consequence in the notes |
|---|---|---|---|---|---|
| B1 | [day5_consultation05 · 128.0 s](../../viewer-test47/index.html#id=day5_consultation05&cond=mixed&t=124) patient | Doctor: "Are you having to go more often than normal?" Patient: "Uh, yeah, a little bit, but I **wasn't** drinking a lot in these days." | "…but I'm **also** drinking a lot in these days" | "…but I'm **also** drinking a lot in these days." | **Both ASR systems heard "not" as "also", reversing the meaning**, and the error went straight into the notes:<br>• 14B × Whisper: "drinking more than usual"<br>• 14B × Qwen3-ASR: "attributed to increased fluid intake"<br>• 27B × Qwen3-ASR: "attributed by the patient to high fluid intake"<br>• gpt-oss × both ASR systems: "increased fluid intake"<br>• For comparison, 27B × human wrote "notes **reduced** fluid intake recently"<br>Frequent urination despite drinking little and frequent urination because of drinking a lot point to different clinical explanations. |
| B2 | [day5_consultation07 · 146.6 s](../../viewer-test47/index.html#id=day5_consultation07&cond=mixed&t=143) (not in grid) doctor → patient | Doctor: "**No** vomiting, diarrhoea now?"<br>Patient: "No." | "…**you're vomiting** diarrhea now no…" | "Yeah, that's fine. Diarrhea now. **Yeah.**" | **Each ASR system makes a different error**:<br>• Whisper turns the negative question into an affirmative statement;<br>• Qwen3-ASR drops "No vomiting" and the patient's "No"; the "Yeah" that follows was actually said by the doctor.<br>The mixed channel has no speaker labels, so both transcripts read as "has vomiting and diarrhoea". |

In the 25 grid consultations, B1 is the only case of a negation replaced by a non-negation (a meaning flip), and Whisper and Qwen3-ASR make it at the same place. Across the 47 test consultations:

- Whisper replaces a clinical negation with a non-negation 6 times and Qwen3-ASR 5 times, see `results/test47/negations/negation_words.csv`;
- most of these merge "no" into a neighbouring word or a backchannel, e.g. "no pain" becomes "okay all right"; B1's not → also is the only one both models share.

## C. Negative findings the generation model added (never asked about)

All of these come from notes written from the **human transcript**, so the ASR plays no part. How they were checked:

1. the judge labelled them "not_mentioned", i.e. absent from the clinician's note;
2. the human transcript was then read through to confirm that neither the doctor nor the patient raised the topic.

| # | Consultation | Note | What the note says | What the transcript has | Why it is dangerous |
|---|---|---|---|---|---|
| C1 | [day5_consultation01](../../viewer-test47/index.html#id=day5_consultation01&cond=mixed&t=56) | gpt-oss × human (gpt-oss × Whisper has the same sentence) | "No nausea, vomiting, visual disturbance, abnormal smells/tastes, fever, **neck stiffness**, or other systemic symptoms." | Headache for a day, sensitive to light. The doctor asked whether coughing or sneezing makes it worse, and about fever and rashes, but **never about the neck**. | Neck stiffness is a red flag for meningitis. An invented "no neck stiffness" in a headache-with-photophobia note makes a reader think it was ruled out. |
| C2 | [day5_consultation01](../../viewer-test47/index.html#id=day5_consultation01&cond=mixed&t=56) | 14B × human | "Relevant negatives: … no recent changes in vision or taste, **no recent trauma**, no recent travel…" | Same consultation; **head injury was never asked about**, nor travel. | Head injury is a red-flag question that must be asked for a new headache. |
| C3 | [day4_consultation05](../../viewer-test47/index.html#id=day4_consultation05&cond=mixed&t=245) | 14B × human | "**No significant weight loss.**" | Abdominal pain, diarrhoea and vomiting; **weight was never discussed**. The patient only said they try not to eat much because they keep going to the toilet. | Weight loss is a red flag for gastrointestinal symptoms. |

**Scale**: in the grid, notes add 2.4–3.5 negative findings on average (see `docs/stage3-grid-results.md`):

- within a generation model, sources barely differ, so this error is determined by the generation model;
- a different ASR system does not fix it.

**How the C cases were selected**: candidates were found with a keyword screen and then checked one by one. Several were excluded because the doctor did ask about the topic:

- clots in day4_consultation07;
- the contraceptive pill in day1_consultation13;
- blood in the urine and past surgery in day5_consultation04;
- radiation to the back in day4_consultation01.

## D. Excluded false cases

- **day4_consultation05 · 408.7 s**: the patient says "I haven't, I haven't noticed any chest pain". The analysis script counts the deleted "not" as a lost negation, but only the **repeated** one was dropped; the meaning is unchanged.
- **day3_consultation02**: the clinician's fact is "No cold (coryzal) symptoms", while the note says the patient "feels cold". The patient did say "I do feel cold quite a lot". This is judging ambiguity from the two senses of "cold" (a common cold vs feeling cold), not an ASR error.
- **day4_consultation06 · 102.0 s**: Qwen3-ASR wrote the doctor's "It's not ten" as "Six out of ten". The patient did rate the pain 6, so the meaning is unchanged.
