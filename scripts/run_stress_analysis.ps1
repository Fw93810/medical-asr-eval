# Stress test: ASR-level analysis of each condition, for both models (Whisper, Qwen3-ASR).
# Per level: raw and corrected WER (evaluate.py), deletion in overlap by role (stress_overlap_roles.py),
# error composition, negations, repetition loops, and the paired bootstrap between the two models.
# Level "clean" is the original mixed channel with the stage-2 runs (copied to clean-<model>, so every
# condition has the same run names). Results go to results/stress/<set>/.
#
# Usage (from the repository root):
#   powershell -File scripts/run_stress_analysis.ps1 -Set test47 -Levels clean,s1_1x,s1_2x,s1_3x
param(
    [Parameter(Mandatory = $true)][string]$Set,
    [Parameter(Mandatory = $true)][string[]]$Levels
)
$Levels = $Levels -split ','
$sci = '.\.venv-sci\Scripts\python.exe'
$out = "results/stress/$Set"
$stage2 = @{ whisper = "outputs/$Set-vad-nocond"; qwen3asr = "outputs/$Set-qwen3-asr-1.7b" }

foreach ($lv in $Levels) {
    $data = if ($lv -eq 'clean') { "data/prepared_$Set" } else { "data/stress/$Set/$lv" }
    $runs = @()
    foreach ($m in 'whisper', 'qwen3asr') {
        $hyp = "outputs/stress/$Set/$lv-$m"
        if ($lv -eq 'clean' -and -not (Test-Path $hyp)) {
            if (-not (Test-Path $stage2[$m])) { continue }
            New-Item -ItemType Directory -Force $hyp | Out-Null
            Get-ChildItem $stage2[$m] -Directory | ForEach-Object {
                New-Item -ItemType Directory -Force "$hyp/$($_.Name)" | Out-Null
                Copy-Item "$($_.FullName)/mixed.json" "$hyp/$($_.Name)/"
            }
        }
        if (Test-Path $hyp) { $runs += "$lv-$m" }
    }
    if (-not $runs) { "[$lv] no runs, skipped"; continue }
    "[$(Get-Date -Format HH:mm)] $lv : $($runs -join ', ')"
    $hyps = $runs | ForEach-Object { "outputs/stress/$Set/$_" }
    foreach ($r in $runs) {
        & $sci -I scripts/evaluate.py --data $data --hyp "outputs/stress/$Set/$r" --results "$out/runs/$r" --terms scispacy 2>&1 | Select-String "Traceback"
        & $sci -I scripts/evaluate.py --data $data --hyp "outputs/stress/$Set/$r" --results "$out/equiv/$r" --terms scispacy --equivalence 2>&1 | Select-String "Traceback"
    }
    & $sci -I scripts/stress_overlap_roles.py --out "$out/$lv/overlap_roles.csv" --runs ($runs | ForEach-Object { "$_=$data,outputs/stress/$Set/$_" }) | Out-Null
    & $sci -I scripts/error_composition.py --data $data --hyp @hyps --out "$out/$lv/composition" 2>&1 | Select-String "Traceback"
    & $sci -I scripts/analyze_negations.py --data $data --hyp @hyps --out "$out/$lv/negations" 2>&1 | Select-String "Traceback"
    & $sci -I scripts/count_repeats.py --data $data --hyp @hyps --out "$out/$lv/repeats" | Out-Null
    & $sci -I scripts/bootstrap_asr.py --data $data --runs @runs --equiv-root "$out/equiv" `
        --composition "$out/$lv/composition/error_ops.csv" --negations "$out/$lv/negations/negation_words.csv" `
        --out "$out/$lv/bootstrap" 2>&1 | Select-String "Traceback|wer_corrected"
}
"[$(Get-Date -Format HH:mm)] analysis done"
