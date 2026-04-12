param(
    [string]$Manifest = "D:\stt_data\fine_tuning\eval_sets\public_baseline\ksponspeech_eval_quick200.jsonl",
    [int]$Limit = 200,
    [string]$PythonExe = "",
    [switch]$IncludeBaseline = $true,
    [switch]$IncludeGhost = $true,
    [switch]$IncludeMoonshine = $false
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$evaluator = Join-Path $repoRoot "server\experiments\stt\evaluate_ksponspeech_baseline.py"

if (-not $PythonExe) {
    $PythonExe = Join-Path $repoRoot "venv\Scripts\python.exe"
}

if (-not (Test-Path $PythonExe)) {
    throw "Python 실행 파일을 찾을 수 없습니다: $PythonExe"
}

if (-not (Test-Path $Manifest)) {
    throw "평가 manifest를 찾을 수 없습니다: $Manifest"
}

$jobs = @()

if ($IncludeBaseline) {
    $jobs += @(
        @{
            Name = "baseline_beam1"
            Args = @(
                $evaluator,
                "--manifest", $Manifest,
                "--limit", $Limit.ToString(),
                "--backend", "faster_whisper",
                "--backend-model", "deepdml/faster-whisper-large-v3-turbo-ct2",
                "--model-path", "D:\caps\server\models\stt\faster-whisper-large-v3-turbo-ct2",
                "--beam-size", "1",
                "--preload",
                "--run-label", "baseline_beam1"
            )
        },
        @{
            Name = "baseline_beam5"
            Args = @(
                $evaluator,
                "--manifest", $Manifest,
                "--limit", $Limit.ToString(),
                "--backend", "faster_whisper",
                "--backend-model", "deepdml/faster-whisper-large-v3-turbo-ct2",
                "--model-path", "D:\caps\server\models\stt\faster-whisper-large-v3-turbo-ct2",
                "--beam-size", "5",
                "--preload",
                "--run-label", "baseline_beam5"
            )
        }
    )
}

if ($IncludeGhost) {
    $jobs += @(
        @{
            Name = "ghost613_beam1"
            Args = @(
                $evaluator,
                "--manifest", $Manifest,
                "--limit", $Limit.ToString(),
                "--backend", "faster_whisper",
                "--backend-model", "ghost613/faster-whisper-large-v3-turbo-korean",
                "--model-path", "D:\caps\server\models\stt\faster-whisper-large-v3-turbo-korean",
                "--beam-size", "1",
                "--preload",
                "--run-label", "ghost613_beam1"
            )
        },
        @{
            Name = "ghost613_beam5"
            Args = @(
                $evaluator,
                "--manifest", $Manifest,
                "--limit", $Limit.ToString(),
                "--backend", "faster_whisper",
                "--backend-model", "ghost613/faster-whisper-large-v3-turbo-korean",
                "--model-path", "D:\caps\server\models\stt\faster-whisper-large-v3-turbo-korean",
                "--beam-size", "5",
                "--preload",
                "--run-label", "ghost613_beam5"
            )
        }
    )
}

if ($IncludeMoonshine) {
    $jobs += @(
        @{
            Name = "moonshine_tiny_ko"
            Args = @(
                $evaluator,
                "--manifest", $Manifest,
                "--limit", $Limit.ToString(),
                "--backend", "moonshine",
                "--backend-model", "moonshine/tiny-ko",
                "--run-label", "moonshine_tiny_ko"
            )
        },
        @{
            Name = "moonshine_base_ko"
            Args = @(
                $evaluator,
                "--manifest", $Manifest,
                "--limit", $Limit.ToString(),
                "--backend", "moonshine",
                "--backend-model", "moonshine/base-ko",
                "--run-label", "moonshine_base_ko"
            )
        }
    )
}

Write-Host "노트 STT 후보 매트릭스 실행"
Write-Host "  python:   $PythonExe"
Write-Host "  manifest: $Manifest"
Write-Host "  samples:  $Limit"
Write-Host "  jobs:     $($jobs.Count)"

foreach ($job in $jobs) {
    Write-Host ""
    Write-Host "=== 실행: $($job.Name) ==="
    & $PythonExe @($job.Args)
    if ($LASTEXITCODE -ne 0) {
        throw "실험이 실패했습니다: $($job.Name)"
    }
}

Write-Host ""
Write-Host "모든 노트 STT 후보 매트릭스 실행이 완료되었습니다."
