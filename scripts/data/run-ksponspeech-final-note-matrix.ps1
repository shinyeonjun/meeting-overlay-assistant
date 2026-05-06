param(
    [string]$Manifest = "D:\stt_data\fine_tuning\eval_sets\public_baseline\ksponspeech_eval_quick200.jsonl",
    [string]$PythonExe = "",
    [string]$Backend = "faster_whisper",
    [string]$BackendModel = "",
    [string]$ModelPath = "",
    [string]$Device = "",
    [string]$ComputeType = "",
    [int]$Limit = 200,
    [string]$BeamSizes = "1,3,5",
    [switch]$Preload
)

$ErrorActionPreference = "Stop"

$scriptsRoot = $PSScriptRoot
$scriptsParent = Split-Path -Parent $scriptsRoot
$repoRoot = Split-Path -Parent $scriptsParent
$evaluator = Join-Path $repoRoot "server\experiments\stt\evaluate_ksponspeech_baseline.py"

if (-not $PythonExe) {
    $PythonExe = Join-Path $repoRoot "venv\Scripts\python.exe"
}

function Invoke-BaselineRun {
    param(
        [int]$BeamSize,
        [string]$RunLabel
    )

    $command = @(
        $PythonExe,
        $evaluator,
        "--manifest", $Manifest,
        "--backend", $Backend,
        "--limit", $Limit,
        "--beam-size", $BeamSize,
        "--run-label", $RunLabel
    )

    if ($BackendModel) {
        $command += @("--backend-model", $BackendModel)
    }
    if ($ModelPath) {
        $command += @("--model-path", $ModelPath)
    }
    if ($Device) {
        $command += @("--device", $Device)
    }
    if ($ComputeType) {
        $command += @("--compute-type", $ComputeType)
    }
    if ($Preload.IsPresent) {
        $command += "--preload"
    }

    Write-Host ""
    Write-Host "실험 시작: $RunLabel"
    Write-Host ("  " + ($command -join " "))
    & $command[0] $command[1..($command.Length - 1)]
}

$beamList = $BeamSizes.Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ } | ForEach-Object { [int]$_ }
if (-not $beamList) {
    throw "BeamSizes에서 유효한 beam size를 찾지 못했습니다."
}

Write-Host "KsponSpeech final note 실험 매트릭스"
Write-Host "  manifest: $Manifest"
Write-Host "  backend:  $Backend"
Write-Host "  limit:    $Limit"
Write-Host "  beams:    $($beamList -join ', ')"

foreach ($beam in $beamList) {
    $label = if ($BackendModel) {
        "$($BackendModel.Replace('/', '-'))-b$beam"
    } else {
        "default-b$beam"
    }
    Invoke-BaselineRun -BeamSize $beam -RunLabel $label
}

Write-Host ""
Write-Host "모든 실험이 끝났습니다."
