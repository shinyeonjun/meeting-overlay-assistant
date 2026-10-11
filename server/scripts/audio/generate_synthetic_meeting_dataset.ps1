param(
    [string]$SourceWav = (Join-Path $PSScriptRoot "..\..\..\tests\fixtures\video\test_16k_mono_15s.wav"),
    [string]$SourceReference = (Join-Path $PSScriptRoot "..\..\..\tests\fixtures\video\test.txt"),
    [string]$OutputDir = (Join-Path $PSScriptRoot "..\..\..\tests\fixtures\video\synthetic_meeting"),
    [int]$SampleRate = 16000,
    [int]$Seed = 20260317
)

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
. (Join-Path $projectRoot "scripts\common\_console_utf8.ps1")
$pythonExe = Join-Path $projectRoot "venv\Scripts\python.exe"
$scriptPath = Join-Path $projectRoot "server\scripts\audio\generate_synthetic_meeting_dataset.py"

& $pythonExe `
    $scriptPath `
    --source-wav $SourceWav `
    --source-reference $SourceReference `
    --output-dir $OutputDir `
    --sample-rate $SampleRate `
    --seed $Seed
