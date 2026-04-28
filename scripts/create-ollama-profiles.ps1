[CmdletBinding()]
param(
    [switch]$SkipPull
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$ollamaDir = Join-Path $repoRoot "server\config\ollama"

function Ensure-OllamaModel {
    param(
        [string]$Name,
        [string]$Modelfile
    )

    $path = Join-Path $ollamaDir $Modelfile
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Modelfile을 찾을 수 없습니다: $path"
    }

    Write-Host "Ollama profile 생성: $Name"
    ollama create $Name -f $path
}

if (-not $SkipPull) {
    Write-Host "기본 모델 pull 확인"
    ollama pull qwen2.5:3b-instruct
    ollama pull qwen2.5:7b-instruct
    ollama pull gemma4:e4b
    ollama pull nomic-embed-text:latest
}

Ensure-OllamaModel `
    -Name "caps-meeting-minutes-qwen3b" `
    -Modelfile "Modelfile.meeting-minutes-qwen2.5-3b"

Ensure-OllamaModel `
    -Name "caps-note-insight-gemma4" `
    -Modelfile "Modelfile.note-insight-gemma4-e4b"

Ensure-OllamaModel `
    -Name "caps-assistant-qwen7b" `
    -Modelfile "Modelfile.assistant-qwen2.5-7b"

Ensure-OllamaModel `
    -Name "caps-live-question-qwen3b" `
    -Modelfile "Modelfile.live-question-qwen2.5-3b"

Write-Host "완료"
