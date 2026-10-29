#!/bin/bash
# Stress-test note level on the rented server: Qwen3.8-27B, 25 grid consultations.
# The human column is regenerated first in the same session, then {5 dB, 0 dB} x {Whisper, Qwen3-ASR}.
# Usage: bash scripts/run_stress_notes.sh  (PYBIN overrides the venv set up by setup_note_server.sh)
set -u
cd "$(dirname "$0")/.."
PYBIN=${PYBIN:-/root/venv/bin/python}
MODEL=qwen3.8:27b-q4_K_M
OUT=notes/stress-qwen3.8-27b
PY="$PYBIN -I scripts/generate_notes.py --data data/prepared_test47 --ids-file results/notes/test47/grid_ids.txt --model $MODEL --think off --out $OUT"
echo "[$(date +%H:%M:%S)] human"
$PY --hyp outputs/stress/test47/s3_snr5-whisper --sources human
for lv in s3_snr5 s3_snr0; do
    for m in whisper qwen3asr; do
        echo "[$(date +%H:%M:%S)] $lv $m"
        $PY --hyp outputs/stress/test47/$lv-$m --asr-name "${lv}_$m" --sources asr_mixed
    done
done
echo "[$(date +%H:%M:%S)] done: $(find "$OUT" -name '*.json' | wc -l) notes"
