$utf8Encoding = New-Object System.Text.UTF8Encoding($false)
[Console]::InputEncoding = $utf8Encoding
[Console]::OutputEncoding = $utf8Encoding
$OutputEncoding = $utf8Encoding
$env:PYTHONIOENCODING = "utf-8"
$null = cmd.exe /c "chcp 65001 > nul"

function Get-DotEnvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$EnvPath,
        [Parameter(Mandatory = $true)]
        [string]$Key,
        [string]$DefaultValue = ""
    )

    if (-not (Test-Path $EnvPath)) {
        return $DefaultValue
    }

    $pattern = '^\s*' + [Regex]::Escape($Key) + '=(.*)$'
    foreach ($line in Get-Content -Path $EnvPath -Encoding UTF8) {
        if ($line -match $pattern) {
            return $matches[1].Trim()
        }
    }

    return $DefaultValue
}

# 워커 간격 값: 명령행 값이 0보다 크면 그대로 쓰고, 아니면 .env 값(없으면 기본값)을 쓴다.
function Resolve-CapsWorkerNumber {
    param(
        [double]$Value,
        [Parameter(Mandatory = $true)]
        [string]$EnvPath,
        [Parameter(Mandatory = $true)]
        [string]$Key,
        [string]$DefaultValue = ""
    )

    if ($Value -gt 0) {
        return $Value
    }

    return [double](Get-DotEnvValue -EnvPath $EnvPath -Key $Key -DefaultValue $DefaultValue)
}

function Get-CapsPythonExe {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    return (Join-Path $Root "venv\Scripts\python.exe")
}

# 파이썬 워커 모듈 실행 골격: 창 제목 → 시작 배너 → 작업 디렉터리 이동 → `python -m <Module> <ModuleArguments>`.
# BannerRows는 @(라벨, 값) 쌍의 배열이다. 라벨 폭은 콘솔 표시 폭(한글 2칸) 기준으로 12칸에 맞춘다.
function Invoke-CapsPythonWorker {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PythonExe,
        [Parameter(Mandatory = $true)]
        [string]$Root,
        [Parameter(Mandatory = $true)]
        [string]$WindowTitle,
        [Parameter(Mandatory = $true)]
        [string]$Module,
        [string[]]$ModuleArguments = @(),
        [Parameter(Mandatory = $true)]
        [string]$Banner,
        [object[]]$BannerRows = @()
    )

    $Host.UI.RawUI.WindowTitle = $WindowTitle
    $arguments = @('-m', $Module) + $ModuleArguments

    Write-Host ""
    Write-Host $Banner -ForegroundColor Cyan
    foreach ($row in $BannerRows) {
        $label = [string]$row[0]
        $width = 0
        foreach ($ch in $label.ToCharArray()) {
            if ([int]$ch -ge 0x1100) { $width += 2 } else { $width += 1 }
        }
        Write-Host ("  " + $label + (" " * [Math]::Max(1, 12 - $width)) + [string]$row[1])
    }
    Write-Host ""

    Set-Location $Root
    & $PythonExe @arguments
}
