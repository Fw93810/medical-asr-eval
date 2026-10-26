"""Regenerate colab_full_run.ipynb, embedding the current scripts via %%writefile
so the notebook runs on Colab without uploading anything.

  python -I scripts/make_colab_notebook.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = ["download_data.py", "prep_data.py", "transcribe.py", "evaluate.py", "medical_terms.txt"]


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(True)}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": text.strip("\n").splitlines(True)}


cells = [
    md("""
# PriMock57 medical ASR evaluation: full run on a Colab GPU

Runs the whole pipeline (download, prep, transcribe, evaluate) on all 57 consultations
with faster-whisper **large-v3**, under three conditions: doctor channel, patient channel,
and a mixed mono "room mic" signal.

1. *Runtime > Change runtime type > GPU* (T4 works; L4/A100 are faster).
2. Run the cells in order. Outputs go to `WORK` (mount Drive so a disconnect doesn't lose them).
   `transcribe.py` skips files that are already done, so you can just re-run after a disconnect.

Data: PriMock57 (Babylon Health), CC BY 4.0. https://github.com/babylonhealth/primock57
"""),
    code("!nvidia-smi"),
    md("## 1. Settings & dependencies"),
    code("""
USE_DRIVE = True          # keep outputs on Google Drive
MODEL = "large-v3"        # or "large-v3-turbo" (faster), "medium", ...
RUN = "fw-" + MODEL       # name of the output / results folder
INITIAL_PROMPT = None     # e.g. "A primary care consultation between a GP and a patient."

import os
if USE_DRIVE:
    from google.colab import drive
    drive.mount("/content/drive")
    WORK = "/content/drive/MyDrive/medasr"
else:
    WORK = "/content/medasr"
os.makedirs(f"{WORK}/scripts", exist_ok=True)
%cd {WORK}
"""),
    code("!pip install -q faster-whisper jiwer whisper_normalizer soundfile"),
    md("""
Optional (untested): scispaCy medical entity extraction for the term-recall metric.
Without it, `evaluate.py` falls back to the bundled lexicon `scripts/medical_terms.txt`.
scispaCy pins an older spaCy, so this may downgrade Colab's spaCy.
"""),
    code("# !pip install -q scispacy https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_sm-0.5.4.tar.gz"),
    md("## 2. Write the pipeline scripts (embedded copies)"),
]
for name in SCRIPTS:
    with open(os.path.join(ROOT, "scripts", name)) as f:
        cells.append(code(f"%%writefile scripts/{name}\n" + f.read()))

cells += [
    md("## 3. Download PriMock57 (~2 GB audio) and prepare the three conditions"),
    code("!python -I scripts/download_data.py --out data/primock57"),
    code("!python -I scripts/prep_data.py --src data/primock57 --out data/prepared"),
    md("## 4. Transcribe (all 57 consultations x doctor / patient / mixed)\n"
       "About 26 h of audio in total (8.6 h per condition). Expect this to take hours on a T4; it resumes if interrupted."),
    code("""
prompt_arg = f'--initial-prompt "{INITIAL_PROMPT}"' if INITIAL_PROMPT else ""
!python -I scripts/transcribe.py --data data/prepared --out outputs/{RUN} --model {MODEL} {prompt_arg}
"""),
    md("## 5. Evaluate"),
    code("!python -I scripts/evaluate.py --data data/prepared --hyp outputs/{RUN} --results results/{RUN}"),
    code("""
import pandas as pd
summary = pd.read_csv(f"results/{RUN}/summary.csv"); display(summary)
wer = pd.read_csv(f"results/{RUN}/wer.csv")
display(wer.pivot(index="id", columns="condition", values="wer").describe())
ins = pd.read_csv(f"results/{RUN}/insertions.csv")
display(ins.sort_values("n_words", ascending=False).head(20))   # longest insertion runs = hallucination candidates
"""),
    code("!cd results && zip -qr /content/{RUN}_results.zip {RUN} && echo saved /content/{RUN}_results.zip"),
    md("""
## Optional: NVIDIA Parakeet TDT 0.6B v2 (untested)
Installing NeMo takes several minutes. Consultations are up to ~14 min; if a T4 runs out of
memory, add `--local-attention`.
"""),
    code("""
# !pip install -q "nemo_toolkit[asr]"
# !python -I scripts/transcribe.py --backend parakeet --model nvidia/parakeet-tdt-0.6b-v2 --data data/prepared --out outputs/parakeet
# !python -I scripts/evaluate.py --data data/prepared --hyp outputs/parakeet --results results/parakeet
"""),
]

nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"provenance": []},
                                    "kernelspec": {"display_name": "Python 3", "name": "python3"},
                                    "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 0}
out = os.path.join(ROOT, "colab_full_run.ipynb")
with open(out, "w") as f:
    json.dump(nb, f, indent=1)
print("wrote", out)
