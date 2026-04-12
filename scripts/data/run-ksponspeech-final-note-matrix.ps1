# 운영 보조 스크립트에서 run ksponspeech final note matrix 작업을 수행한다.
ì ìííë¤.
﻿param(
    [string]$Manifest = "D:\stt_data\fine_tuning\eval_sets\public_baseline\ksponspeech_eval_quick200.jsonl",
    [string]$PythonExe = "D:\caps\venv\Scripts\python.exe",
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

function Invoke-BaselineRun {
    param(
        [int]$BeamSize,
        [string]$RunLabel
    )

    $command = @(
        $PythonExe,
        "D:\caps\server\experiments\stt\evaluate_ksponspeech_baseline.py",
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
