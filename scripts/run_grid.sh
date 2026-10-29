#!/bin/bash
# Note grid on the rented server: each generation model x four inputs x 25 test consultations.
# Usage: bash scripts/run_grid.sh <ollama model> <output name> [think]  (PYBIN overrides the venv)
set -u
cd "$(dirname "$0")/.."
PYBIN=${PYBIN:-/root/venv/bin/python}
PY="$PYBIN -I scripts/generate_notes.py --data data/prepared_test47 --ids-file results/notes/test47/grid_ids.txt"
MODEL=$1; NAME=$2; THINK=${3:-off}
OUT=notes/$NAME
echo "[$(date +%H:%M:%S)] $MODEL -> $OUT (think $THINK)"
$PY --model "$MODEL" --think "$THINK" --hyp outputs/test47-vad-nocond --sources human human_plain asr_mixed --out "$OUT"
$PY --model "$MODEL" --think "$THINK" --hyp outputs/test47-qwen3-asr-1.7b --asr-name qwen3asr --sources asr_mixed --out "$OUT"
echo "[$(date +%H:%M:%S)] done $MODEL: $(find "$OUT" -name '*.json' | wc -l) notes"
