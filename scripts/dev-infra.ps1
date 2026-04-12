param(
    [ValidateSet("up", "down", "logs", "status", "restart", "psql", "redis-cli")]
    [string]$Action = "up",
    [ValidateSet("all", "postgresql", "redis")]
    [string]$Service = "all"
)

$scriptsRoot = $PSScriptRoot
$root = Split-Path -Parent $scriptsRoot
. (Join-Path $scriptsRoot "common\_console_utf8.ps1")

$composeFile = Join-Path $root "deploy\server\docker-compose.infrastructure.yml"
$defaultPostgresDsn = "postgresql://caps:caps@127.0.0.1:55432/caps"
$defaultRedisUrl = "redis://127.0.0.1:56379/0"

if (-not (Test-Path $composeFile)) {
    Write-Error "인프라 compose 파일을 찾을 수 없습니다: $composeFile"
    exit 1
}

Set-Location $root

$targetServices = @()
if ($Service -eq "all") {
    $targetServices = @("postgresql", "redis")
} else {
    $targetServices = @($Service)
}

switch ($Action) {
    "up" {
        Write-Host ""
        Write-Host "로컬 개발 인프라 시작" -ForegroundColor Cyan
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
            Write-Error "psql 액션은 PostgreSQL 서비스에서만 사용할 수 있습니다."
            exit 1
        }
        docker compose -f $composeFile exec postgresql psql -U caps -d caps
    }
    "redis-cli" {
        if ($Service -eq "postgresql") {
            Write-Error "redis-cli 액션은 Redis 서비스에서만 사용할 수 있습니다."
            exit 1
        }
        docker compose -f $composeFile exec redis redis-cli
    }
}
