param(
    [string]$HostAddress = "",
    [int]$ControlPort = 0,
    [int]$LivePort = 0,
    [int]$WaitMilliseconds = 1200,
    [switch]$SkipOverlay,
    [switch]$SkipWeb,
    [switch]$SkipReportWorker,
    [switch]$SkipLiveQuestionWorker,
    [switch]$Preview
)

$scriptsRoot = $PSScriptRoot
$root = Split-Path -Parent $scriptsRoot
. (Join-Path $scriptsRoot "common\_console_utf8.ps1")

$serverScript = Join-Path $scriptsRoot "dev-server.ps1"
$clientScript = Join-Path $scriptsRoot "dev-client.ps1"
$reportWorkerScript = Join-Path $scriptsRoot "dev-report-worker.ps1"
$liveQuestionWorkerScript = Join-Path $scriptsRoot "dev-live-question-worker.ps1"
$powershellExe = (Get-Command powershell.exe -ErrorAction Stop).Source
$envPath = Join-Path $root ".env"

$resolvedHostAddress = if ($HostAddress) {
    $HostAddress
} else {
    Get-DotEnvValue -EnvPath $envPath -Key "SERVER_HOST" -DefaultValue "127.0.0.1"
}
$resolvedControlPort = if ($ControlPort -gt 0) {
    $ControlPort
} else {
    [int](Get-DotEnvValue -EnvPath $envPath -Key "SERVER_PORT" -DefaultValue "8011")
}
$resolvedLivePort = if ($LivePort -gt 0) {
    $LivePort
} else {
    [int](Get-DotEnvValue -EnvPath $envPath -Key "LIVE_SERVER_PORT" -DefaultValue "8012")
}

if (-not (Test-Path $serverScript)) {
    Write-Error "서버 실행 스크립트를 찾을 수 없습니다: $serverScript"
    exit 1
}

if (-not (Test-Path $clientScript)) {
    Write-Error "클라이언트 실행 스크립트를 찾을 수 없습니다: $clientScript"
    exit 1
}

if (-not (Test-Path $reportWorkerScript)) {
    Write-Error "리포트 워커 실행 스크립트를 찾을 수 없습니다: $reportWorkerScript"
    exit 1
}

if (-not (Test-Path $liveQuestionWorkerScript)) {
    Write-Error "실시간 질문 워커 실행 스크립트를 찾을 수 없습니다: $liveQuestionWorkerScript"
    exit 1
}

$controlArguments = @(
    "-NoExit",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $serverScript,
    "-HostAddress", $resolvedHostAddress,
    "-Port", "$resolvedControlPort",
    "-EntryPoint", "server.app.entrypoints.control_api:app"
)

$liveArguments = @(
    "-NoExit",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $serverScript,
    "-HostAddress", $resolvedHostAddress,
    "-Port", "$resolvedLivePort",
    "-EntryPoint", "server.app.entrypoints.live_api:app"
)

$reportWorkerArguments = @(
    "-NoExit",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $reportWorkerScript
)

$liveQuestionWorkerArguments = @(
    "-NoExit",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $liveQuestionWorkerScript
)

$overlayArguments = @(
    "-NoExit",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $clientScript,
    "-Target", "overlay"
)

$webArguments = @(
    "-NoExit",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $clientScript,
    "-Target", "web"
)

Write-Host ""
Write-Host "CAPS split 개발 스택 실행" -ForegroundColor Cyan
Write-Host "  control:       http://$resolvedHostAddress`:$resolvedControlPort"
Write-Host "  live:          http://$resolvedHostAddress`:$resolvedLivePort"
Write-Host "  overlay:       $(-not $SkipOverlay)"
Write-Host "  web:           $(-not $SkipWeb)"
Write-Host "  report worker: $(-not $SkipReportWorker)"
Write-Host "  live question: $(-not $SkipLiveQuestionWorker)"
Write-Host "  서버 대기:     ${WaitMilliseconds}ms"
Write-Host ""

if ($Preview) {
    Write-Host "미리보기 모드입니다. 실제 프로세스는 시작하지 않습니다." -ForegroundColor Yellow
    Write-Host "  powershell.exe $($controlArguments -join ' ')"
    Write-Host "  powershell.exe $($liveArguments -join ' ')"
    if (-not $SkipReportWorker) {
        Write-Host "  powershell.exe $($reportWorkerArguments -join ' ')"
    }
    if (-not $SkipLiveQuestionWorker) {
        Write-Host "  powershell.exe $($liveQuestionWorkerArguments -join ' ')"
    }
    if (-not $SkipOverlay) {
        Write-Host "  powershell.exe $($overlayArguments -join ' ')"
    }
    if (-not $SkipWeb) {
        Write-Host "  powershell.exe $($webArguments -join ' ')"
    }
    exit 0
}

$processes = @()

$controlProcess = Start-Process `
    -FilePath $powershellExe `
    -ArgumentList $controlArguments `
    -WorkingDirectory $root `
    -PassThru
$processes += [PSCustomObject]@{
    Name = "control-server"
    Process = $controlProcess
}

Start-Sleep -Milliseconds $WaitMilliseconds

$liveProcess = Start-Process `
    -FilePath $powershellExe `
    -ArgumentList $liveArguments `
    -WorkingDirectory $root `
    -PassThru
$processes += [PSCustomObject]@{
    Name = "live-server"
    Process = $liveProcess
}

Start-Sleep -Milliseconds 800

if (-not $SkipReportWorker) {
    $reportWorkerProcess = Start-Process `
        -FilePath $powershellExe `
        -ArgumentList $reportWorkerArguments `
        -WorkingDirectory $root `
        -PassThru
    $processes += [PSCustomObject]@{
        Name = "report-worker"
        Process = $reportWorkerProcess
    }

    Start-Sleep -Milliseconds 400
}

if (-not $SkipLiveQuestionWorker) {
    $liveQuestionWorkerProcess = Start-Process `
        -FilePath $powershellExe `
        -ArgumentList $liveQuestionWorkerArguments `
        -WorkingDirectory $root `
        -PassThru
    $processes += [PSCustomObject]@{
        Name = "live-question"
        Process = $liveQuestionWorkerProcess
    }

    Start-Sleep -Milliseconds 300
}

if (-not $SkipOverlay) {
    $overlayProcess = Start-Process `
        -FilePath $powershellExe `
        -ArgumentList $overlayArguments `
        -WorkingDirectory $root `
        -PassThru
    $processes += [PSCustomObject]@{
        Name = "overlay"
        Process = $overlayProcess
    }

    Start-Sleep -Milliseconds 400
}

if (-not $SkipWeb) {
    $webProcess = Start-Process `
        -FilePath $powershellExe `
        -ArgumentList $webArguments `
        -WorkingDirectory $root `
        -PassThru
    $processes += [PSCustomObject]@{
        Name = "web"
        Process = $webProcess
    }
}

Write-Host "split 개발 스택이 시작되었습니다." -ForegroundColor Green
foreach ($item in $processes) {
    Write-Host ("  {0,-15} PID {1}" -f $item.Name, $item.Process.Id)
}

Write-Host ""
Write-Host "종료 방법" -ForegroundColor Cyan
$pidList = ($processes | ForEach-Object { $_.Process.Id }) -join ","
Write-Host "  각 창을 직접 닫거나 Stop-Process -Id $pidList"
