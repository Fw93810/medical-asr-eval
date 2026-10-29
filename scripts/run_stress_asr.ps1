# Stress test: transcribe the mixed channel of synthesised conditions with the two stage-2 settings.
#   Whisper large-v3: --vad --no-condition-on-previous-text (test47-vad-nocond)
#   Qwen3-ASR-1.7B: shared chunk plan from plan_chunks.py, re-planned on each condition's own audio
# One GPU job at a time. Finished files are skipped, so the script can be re-run after an interruption.
#
# Usage (from the repository root; -HfHome sets the Hugging Face model cache, default $env:HF_HOME):
#   powershell -File scripts/run_stress_asr.ps1 -Root data/stress/full10 -Set full10 -Levels s1_1x,s1_2x,s1_3x -HfHome D:\cache\huggingface
param(
    [Parameter(Mandatory = $true)][string]$Root,
    [Parameter(Mandatory = $true)][string]$Set,
    [Parameter(Mandatory = $true)][string[]]$Levels,
    [string]$HfHome = $env:HF_HOME
)
$Levels = $Levels -split ','  # "powershell -File" passes a comma list as one string
if ($HfHome) { $env:HF_HOME = $HfHome }
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = '1'
$env:PYTHONUNBUFFERED = '1'

foreach ($lv in $Levels) {
    $data = "$Root/$lv"
    $chunks = "outputs/chunks/stress/$Set/$lv"
    "[$(Get-Date -Format HH:mm)] $lv chunk plan"
    & .\.venv\Scripts\python.exe -I scripts/plan_chunks.py --data $data --out $chunks --conditions mixed
    "[$(Get-Date -Format HH:mm)] $lv whisper"
    & .\.venv\Scripts\python.exe -I scripts/transcribe.py --backend faster-whisper --model large-v3 --device cuda `
        --vad --no-condition-on-previous-text --conditions mixed --data $data --out "outputs/stress/$Set/$lv-whisper" 2>&1 |
        Select-String "per audio-minute|Error|Traceback" | Select-Object -Last 2
    "[$(Get-Date -Format HH:mm)] $lv qwen3asr"
    & .\.venv-qwen\Scripts\python.exe -I scripts/transcribe.py --backend qwen3asr --chunks $chunks --conditions mixed `
        --data $data --out "outputs/stress/$Set/$lv-qwen3asr" 2>&1 |
        Select-String "per audio-minute|Error|Traceback" | Select-Object -Last 2
}
"[$(Get-Date -Format HH:mm)] done"
