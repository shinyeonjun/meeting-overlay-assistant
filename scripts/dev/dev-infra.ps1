# 개발 실행 스크립트에서 dev infra 작업을 수행한다.
ì ìííë¤.
param(
    [ValidateSet("up", "down", "logs", "status", "restart", "psql", "redis-cli")]
    [string]$Action = "up",
    [ValidateSet("all", "postgresql", "redis")]
    [string]$Service = "all"
)

$scriptsRoot = $PSScriptRoot
$scriptsParent = Split-Path -Parent $scriptsRoot
$root = Split-Path -Parent $scriptsParent
. (Join-Path $scriptsParent "common\_console_utf8.ps1")

function Test-DockerDaemon {
    $null = & docker version --format "{{.Server.Version}}" 2>$null
    return ($LASTEXITCODE -eq 0)
}

$composeFile = Join-Path $root "deploy\server\docker-compose.infrastructure.yml"
$defaultPostgresDsn = "postgresql://caps:caps@127.0.0.1:55432/caps"
$defaultRedisUrl = "redis://127.0.0.1:56379/0"

if (-not (Test-Path $composeFile)) {
    Write-Error "Infrastructure compose file not found: $composeFile"
    exit 1
}

Set-Location $root

if (-not (Test-DockerDaemon)) {
    Write-Host "Docker daemon에 연결할 수 없습니다." -ForegroundColor Red
    Write-Host "Docker Desktop을 먼저 실행한 뒤 다시 시도하세요." -ForegroundColor Yellow
    exit 1
}

$targetServices = @()
if ($Service -eq "all") {
    $targetServices = @("postgresql", "redis")
} else {
    $targetServices = @($Service)
}

switch ($Action) {
    "up" {
        Write-Host ""
        Write-Host "Local infrastructure start" -ForegroundColor Cyan
        Write-Host "  compose:   $composeFile"
        Write-Host "  services:  $($targetServices -join ', ')"
        Write-Host "  postgres:  $defaultPostgresDsn"
        Write-Host "  redis:     $defaultRedisUrl"
        Write-Host ""
        docker compose -f $composeFile up -d @targetServices
    }
    "down" {
        if ($Service -eq "all") {
            docker compose -f $composeFile down
        } else {
            docker compose -f $composeFile stop @targetServices
            docker compose -f $composeFile rm -f @targetServices
        }
    }
    "logs" {
        if ($Service -eq "all") {
            docker compose -f $composeFile logs -f
        } else {
            docker compose -f $composeFile logs -f @targetServices
        }
    }
    "status" {
        docker compose -f $composeFile ps
    }
    "restart" {
        docker compose -f $composeFile restart @targetServices
    }
    "psql" {
        if ($Service -eq "redis") {
            Write-Error "psql is only available for the PostgreSQL service."
            exit 1
        }
        docker compose -f $composeFile exec postgresql psql -U caps -d caps
    }
    "redis-cli" {
        if ($Service -eq "postgresql") {
            Write-Error "redis-cli is only available for the Redis service."
            exit 1
        }
        docker compose -f $composeFile exec redis redis-cli
    }
}
