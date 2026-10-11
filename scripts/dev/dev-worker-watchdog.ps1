# 워커 스크립트를 감시하며, 종료되면 잠시 뒤 다시 띄운다.
# 로그는 server/data/logs/<이름>.log에 덧붙여 남긴다.
param(
    [Parameter(Mandatory = $true)]
    [string]$WorkerScript,
    [Parameter(Mandatory = $true)]
    [string]$Name,
    [int]$RestartDelaySeconds = 5
)

$scriptsRoot = $PSScriptRoot
$scriptsParent = Split-Path -Parent $scriptsRoot
$root = Split-Path -Parent $scriptsParent
. (Join-Path $scriptsParent "common\_console_utf8.ps1")
$Host.UI.RawUI.WindowTitle = "CAPS watchdog: $Name"
$powershellExe = (Get-Command powershell.exe -ErrorAction Stop).Source

$logDir = Join-Path $root "server\data\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logPath = Join-Path $logDir "$Name.log"

Set-Location $root
while ($true) {
    $stamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    "[$stamp] $Name 시작" | Tee-Object -FilePath $logPath -Append | Write-Host

    & $powershellExe -NoProfile -ExecutionPolicy Bypass -File $WorkerScript *>&1 |
        Tee-Object -FilePath $logPath -Append | Write-Host
    $exitCode = $LASTEXITCODE

    $stamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    "[$stamp] $Name 종료 (exit=$exitCode), ${RestartDelaySeconds}초 뒤 재시작" |
        Tee-Object -FilePath $logPath -Append | Write-Host
    Start-Sleep -Seconds $RestartDelaySeconds
}
