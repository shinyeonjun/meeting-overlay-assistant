param(
    [ValidateSet("up", "down", "logs", "psql", "status")]
    [string]$Action = "up"
)

$scriptsRoot = $PSScriptRoot
$root = Split-Path -Parent $scriptsRoot
. (Join-Path $scriptsRoot "common\_console_utf8.ps1")

$composeFile = Join-Path $root "deploy\server\docker-compose.postgresql.yml"
$serviceName = "postgresql"
$defaultDsn = "postgresql://caps:caps@127.0.0.1:55432/caps"

if (-not (Test-Path $composeFile)) {
    Write-Error "PostgreSQL compose 파일을 찾을 수 없습니다: $composeFile"
    exit 1
}

Set-Location $root

switch ($Action) {
    "up" {
        Write-Host ""
        Write-Host "로컬 PostgreSQL 시작" -ForegroundColor Cyan
        Write-Host "  compose: $composeFile"
        Write-Host "  dsn:     $defaultDsn"
        Write-Host ""
        docker compose -f $composeFile up -d
    }
    "down" {
        docker compose -f $composeFile down
    }
    "logs" {
        docker compose -f $composeFile logs -f $serviceName
    }
    "psql" {
        docker compose -f $composeFile exec $serviceName psql -U caps -d caps
    }
    "status" {
        docker compose -f $composeFile ps
    }
}
