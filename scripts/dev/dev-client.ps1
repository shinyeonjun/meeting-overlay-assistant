param(
    [ValidateSet("overlay", "web")]
    [string]$Target = "overlay",
    [string]$ControlApiBaseUrl = "",
    [string]$LiveApiBaseUrl = "",
    [switch]$BuildOnly
)

$scriptsRoot = $PSScriptRoot
$scriptsParent = Split-Path -Parent $scriptsRoot
$root = Split-Path -Parent $scriptsParent
. (Join-Path $scriptsParent "common\_console_utf8.ps1")
$Host.UI.RawUI.WindowTitle = "CAPS client $Target"
$clientDir = Join-Path $root "client\$Target"
$envPath = Join-Path $root ".env"

if (-not (Test-Path $clientDir)) {
    Write-Error "클라이언트 디렉터리를 찾을 수 없습니다: $clientDir"
    exit 1
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Error "npm 실행 파일을 찾을 수 없습니다. Node.js 설치를 확인해 주세요."
    exit 1
}

$command = switch ($Target) {
    "overlay" {
        if ($BuildOnly) { "overlay:build" } else { "overlay:tauri:dev" }
        break
    }
    "web" {
        if ($BuildOnly) { "web:build" } else { "web:dev" }
        break
    }
}

function Set-EnvDefault {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Key,
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    if (-not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($Key, "Process"))) {
        return
    }
    if ([string]::IsNullOrWhiteSpace($Value)) {
        return
    }

    [Environment]::SetEnvironmentVariable($Key, $Value, "Process")
}

if ($Target -eq "overlay") {
    $resolvedControlApiBaseUrl = if ($ControlApiBaseUrl) {
        $ControlApiBaseUrl
    } else {
        $controlPort = Get-DotEnvValue -EnvPath $envPath -Key "SERVER_PORT" -DefaultValue "8011"
        "http://127.0.0.1:$controlPort"
    }
    $resolvedLiveApiBaseUrl = if ($LiveApiBaseUrl) {
        $LiveApiBaseUrl
    } else {
        $livePort = Get-DotEnvValue -EnvPath $envPath -Key "LIVE_SERVER_PORT" -DefaultValue "8012"
        "http://127.0.0.1:$livePort"
    }

    Set-EnvDefault -Key "VITE_CONTROL_API_BASE_URL" -Value $resolvedControlApiBaseUrl
    Set-EnvDefault -Key "VITE_LIVE_API_BASE_URL" -Value $resolvedLiveApiBaseUrl

    $defaultBackendPython = Join-Path $root ".venv\Scripts\python.exe"
    $defaultLiveAudioScriptPath = Join-Path $root "server\scripts\audio\stream_live_audio_ws.py"
    if (Test-Path $defaultBackendPython) {
        Set-EnvDefault -Key "VITE_BACKEND_PYTHON" -Value $defaultBackendPython
    }
    if (Test-Path $defaultLiveAudioScriptPath) {
        Set-EnvDefault -Key "VITE_LIVE_AUDIO_SCRIPT_PATH" -Value $defaultLiveAudioScriptPath
    }
}

Write-Host ""
Write-Host "CAPS 클라이언트 실행" -ForegroundColor Cyan
Write-Host "  대상:     $Target"
Write-Host "  루트:     $clientDir"
Write-Host "  명령:     npm run $command"
if ($Target -eq "overlay") {
    Write-Host "  control:  $env:VITE_CONTROL_API_BASE_URL"
    Write-Host "  live:     $env:VITE_LIVE_API_BASE_URL"
    Write-Host "  python:   $env:VITE_BACKEND_PYTHON"
    Write-Host "  audio:    $env:VITE_LIVE_AUDIO_SCRIPT_PATH"
} else {
    Write-Host "  API URL:  .env.example 기준 web=8011"
}
Write-Host ""

Set-Location $clientDir
npm run $command
