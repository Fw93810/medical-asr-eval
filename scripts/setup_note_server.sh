#!/bin/bash
# Rented-GPU setup for note generation (stage-3 grid and stress-test note level): Ollama 0.40.11,
# Qwen3.8-27B Q4_K_M, and a Python venv for generate_notes.py. Run as root on a fresh Ubuntu pod:
#   bash setup_note_server.sh
set -eux
export DEBIAN_FRONTEND=noninteractive
command -v zstd >/dev/null || (apt-get update -qq && apt-get install -y -qq zstd curl pciutils lshw >/dev/null)
curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION=0.40.11 sh
ollama --version || true
nohup ollama serve > /root/ollama.log 2>&1 &
sleep 5
ollama --version
ollama pull qwen3.8:27b-q4_K_M
python3 -m venv /root/venv
/root/venv/bin/pip install -q jiwer whisper-normalizer
echo SETUP_DONE
