# 개발 실행 스크립트에서 dev stack 작업을 수행한다.
param(
    [string]$HostAddress = "",
    [int]$ControlPort = 0,
    [int]$LivePort = 0,
    [int]$WaitMilliseconds = 1200,
    [switch]$SkipOverlay,
    [switch]$SkipWeb,
    [switch]$SkipPostProcessingWorker,
    [switch]$SkipNoteCorrectionWorker,
    [switch]$SkipReportWorker,
    [switch]$SkipLiveQuestionWorker,
    [switch]$Preview
)

$scriptsRoot = $PSScriptRoot
$scriptsParent = Split-Path -Parent $scriptsRoot
$root = Split-Path -Parent $scriptsParent
. (Join-Path $scriptsParent "common\_console_utf8.ps1")

function Test-TcpPort {
    param(
        [Parameter(Mandatory = $true)]
        [string]$HostName,
        [Parameter(Mandatory = $true)]
        [int]$Port,
        [int]$TimeoutMilliseconds = 1200
    )

    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $asyncResult = $client.BeginConnect($HostName, $Port, $null, $null)
        if (-not $asyncResult.AsyncWaitHandle.WaitOne($TimeoutMilliseconds, $false)) {
            return $false
        }
        $client.EndConnect($asyncResult)
        return $true
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

function Get-HostFromUri {
    param(
        [Parameter(Mandatory = $true)]
        [string]$UriText,
        [string]$DefaultHost = "127.0.0.1"
    )

    try {
        return ([System.Uri]$UriText).Host
    } catch {
        return $DefaultHost
    }
}

function Get-PortFromUri {
    param(
        [Parameter(Mandatory = $true)]
        [string]$UriText,
        [int]$DefaultPort
    )

    try {
        $uri = [System.Uri]$UriText
        if ($uri.Port -gt 0) {
            return $uri.Port
        }
    } catch {
    }
    return $DefaultPort
}

$serverScript = Join-Path $scriptsRoot "dev-server.ps1"
$clientScript = Join-Path $scriptsRoot "dev-client.ps1"
$postProcessingWorkerScript = Join-Path $scriptsRoot "dev-post-processing-worker.ps1"
$noteCorrectionWorkerScript = Join-Path $scriptsRoot "dev-note-correction-worker.ps1"
$reportWorkerScript = Join-Path $scriptsRoot "dev-report-worker.ps1"
$liveQuestionWorkerScript = Join-Path $scriptsRoot "dev-live-question-worker.ps1"
$powershellExe = (Get-Command powershell.exe -ErrorAction Stop).Source
$envPath = Join-Path $root ".env"
$postgresqlDsn = Get-DotEnvValue -EnvPath $envPath -Key "POSTGRESQL_DSN" -DefaultValue "postgresql://caps:caps@127.0.0.1:55432/caps"
$redisUrl = Get-DotEnvValue -EnvPath $envPath -Key "REDIS_URL" -DefaultValue "redis://127.0.0.1:56379/0"
$postgresHost = Get-HostFromUri -UriText $postgresqlDsn -DefaultHost "127.0.0.1"
$postgresPort = Get-PortFromUri -UriText $postgresqlDsn -DefaultPort 55432
$redisHost = Get-HostFromUri -UriText $redisUrl -DefaultHost "127.0.0.1"
$redisPort = Get-PortFromUri -UriText $redisUrl -DefaultPort 56379
$liveQuestionAnalysisEnabled = (Get-DotEnvValue -EnvPath $envPath -Key "LIVE_QUESTION_ANALYSIS_ENABLED" -DefaultValue "false").Trim().ToLowerInvariant()
$enabledTokens = @("1", "true", "yes", "on")
$liveQuestionDisabledByEnv = -not ($enabledTokens -contains $liveQuestionAnalysisEnabled)

if ($liveQuestionDisabledByEnv -and -not $SkipLiveQuestionWorker) {
    $SkipLiveQuestionWorker = $true
}

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

if (-not (Test-Path $postProcessingWorkerScript)) {
    Write-Error "후처리 워커 실행 스크립트를 찾을 수 없습니다: $postProcessingWorkerScript"
    exit 1
}

if (-not (Test-Path $noteCorrectionWorkerScript)) {
    Write-Error "노트 보정 워커 실행 스크립트를 찾을 수 없습니다: $noteCorrectionWorkerScript"
    exit 1
}

if (-not (Test-Path $reportWorkerScript)) {
    Write-Error "회의록 워커 실행 스크립트를 찾을 수 없습니다: $reportWorkerScript"
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

$postProcessingWorkerArguments = @(
    "-NoExit",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $postProcessingWorkerScript
)

$noteCorrectionWorkerArguments = @(
    "-NoExit",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $noteCorrectionWorkerScript
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
Write-Host "  postgresql:    $postgresHost`:$postgresPort"
Write-Host "  redis:         $redisHost`:$redisPort"
Write-Host "  overlay:       $(-not $SkipOverlay)"
Write-Host "  web:           $(-not $SkipWeb)"
Write-Host "  post worker:   $(-not $SkipPostProcessingWorker)"
Write-Host "  note worker:   $(-not $SkipNoteCorrectionWorker)"
Write-Host "  report worker: $(-not $SkipReportWorker)"
Write-Host "  live question: $(if ($liveQuestionDisabledByEnv) { 'false (LIVE_QUESTION_ANALYSIS_ENABLED=false)' } else { -not $SkipLiveQuestionWorker })"
Write-Host "  서버 대기:     ${WaitMilliseconds}ms"
Write-Host ""

if ($Preview) {
    Write-Host "미리보기 모드입니다. 실제 프로세스는 시작하지 않습니다." -ForegroundColor Yellow
    Write-Host "  powershell.exe $($controlArguments -join ' ')"
    Write-Host "  powershell.exe $($liveArguments -join ' ')"
    if (-not $SkipPostProcessingWorker) {
        Write-Host "  powershell.exe $($postProcessingWorkerArguments -join ' ')"
    }
    if (-not $SkipNoteCorrectionWorker) {
        Write-Host "  powershell.exe $($noteCorrectionWorkerArguments -join ' ')"
    }
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

$missingInfra = @()
if (-not (Test-TcpPort -HostName $postgresHost -Port $postgresPort)) {
    $missingInfra += "PostgreSQL($postgresHost`:$postgresPort)"
}
if (-not (Test-TcpPort -HostName $redisHost -Port $redisPort)) {
    $missingInfra += "Redis($redisHost`:$redisPort)"
}

if ($missingInfra.Count -gt 0) {
    Write-Host "필수 인프라가 아직 준비되지 않았습니다." -ForegroundColor Red
    foreach ($item in $missingInfra) {
        Write-Host "  - $item" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "먼저 아래 명령으로 인프라를 올린 뒤 다시 실행하세요." -ForegroundColor Cyan
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\\scripts\\dev-infra.ps1 up"
    Write-Host ""
    Write-Host "Docker Desktop이 꺼져 있으면 먼저 실행해야 합니다." -ForegroundColor DarkYellow
    exit 1
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

if (-not $SkipPostProcessingWorker) {
    $postProcessingWorkerProcess = Start-Process `
        -FilePath $powershellExe `
        -ArgumentList $postProcessingWorkerArguments `
        -WorkingDirectory $root `
        -PassThru
    $processes += [PSCustomObject]@{
        Name = "post-worker"
        Process = $postProcessingWorkerProcess
    }

    Start-Sleep -Milliseconds 400
}

if (-not $SkipNoteCorrectionWorker) {
    $noteCorrectionWorkerProcess = Start-Process `
        -FilePath $powershellExe `
        -ArgumentList $noteCorrectionWorkerArguments `
        -WorkingDirectory $root `
        -PassThru
    $processes += [PSCustomObject]@{
        Name = "note-correction-worker"
        Process = $noteCorrectionWorkerProcess
    }
}

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
