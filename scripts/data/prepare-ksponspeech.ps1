param(
    [string]$SourcePartsPath = "D:\stt_data\10.한국어음성",
    [string]$WorkingRoot = "D:\stt_data\fine_tuning",
    [string[]]$Only = @(),
    [switch]$DryRun,
    [switch]$ForceRebuild,
    [switch]$ForceExtract,
    [switch]$SkipExtract
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Ensure-Directory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Get-PartOffset {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $match = [regex]::Match($Name, "\.part(\d+)$")
    if (-not $match.Success) {
        throw "part 오프셋을 해석할 수 없습니다: $Name"
    }
    return [int64]$match.Groups[1].Value
}

function Get-ArchiveBaseName {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $match = [regex]::Match($Name, "^(?<base>.+\.zip)\.part\d+$")
    if (-not $match.Success) {
        throw "part 파일 이름 형식을 해석할 수 없습니다: $Name"
    }
    return $match.Groups["base"].Value
}

function Join-ArchiveParts {
    param(
        [Parameter(Mandatory = $true)]
        [System.IO.FileInfo[]]$Parts,
        [Parameter(Mandatory = $true)]
        [string]$DestinationPath,
        [switch]$DryRun,
        [switch]$Force
    )

    if ((Test-Path -LiteralPath $DestinationPath) -and (-not $Force)) {
        Write-Host "이미 zip이 있어 재생성하지 않습니다: $DestinationPath" -ForegroundColor DarkYellow
        return
    }

    if ($DryRun) {
        Write-Host "[DryRun] zip 생성: $DestinationPath" -ForegroundColor Yellow
        return
    }

    $targetStream = [System.IO.File]::Open($DestinationPath, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write)
    try {
        foreach ($part in $Parts) {
            Write-Host ("  part 결합: {0} ({1:N2} MB)" -f $part.Name, ($part.Length / 1MB)) -ForegroundColor DarkGray
            $sourceStream = [System.IO.File]::OpenRead($part.FullName)
            try {
                $sourceStream.CopyTo($targetStream)
            } finally {
                $sourceStream.Dispose()
            }
        }
    } finally {
        $targetStream.Dispose()
    }
}

function Resolve-ExtractTarget {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ArchiveBaseName,
        [Parameter(Mandatory = $true)]
        [string]$ExtractRoot
    )

    switch -Regex ($ArchiveBaseName) {
        "^KsponSpeech_scripts\.zip$" { return (Join-Path $ExtractRoot "scripts") }
        "^KsponSpeech_eval\.zip$" { return (Join-Path $ExtractRoot "eval") }
        "^KsponSpeech_\d+\.zip$" { return (Join-Path $ExtractRoot "train") }
        default { return (Join-Path $ExtractRoot "misc") }
    }
}

function Expand-KsponArchive {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ZipPath,
        [Parameter(Mandatory = $true)]
        [string]$DestinationPath,
        [switch]$DryRun,
        [switch]$Force
    )

    Ensure-Directory -Path $DestinationPath
    $hasExistingItems = (Get-ChildItem -LiteralPath $DestinationPath -Force -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0
    if ($hasExistingItems -and (-not $Force)) {
        Write-Host "이미 압축 해제된 폴더가 있어 건너뜁니다: $DestinationPath" -ForegroundColor DarkYellow
        return
    }

    if ($DryRun) {
        Write-Host "[DryRun] 압축 해제: $ZipPath -> $DestinationPath" -ForegroundColor Yellow
        return
    }

    if ($Force -and $hasExistingItems) {
        Get-ChildItem -LiteralPath $DestinationPath -Force | Remove-Item -Recurse -Force
    }

    Expand-Archive -LiteralPath $ZipPath -DestinationPath $DestinationPath -Force
}

$rawRoot = Join-Path $WorkingRoot "raw\ksponspeech"
$zipRoot = Join-Path $rawRoot "zips"
$extractRoot = Join-Path $WorkingRoot "extracted\ksponspeech"

Ensure-Directory -Path $zipRoot
Ensure-Directory -Path $extractRoot

if (-not (Test-Path -LiteralPath $SourcePartsPath)) {
    throw "원본 part 폴더를 찾을 수 없습니다: $SourcePartsPath"
}

$partFiles = Get-ChildItem -LiteralPath $SourcePartsPath -File | Where-Object {
    $_.Name -match "\.zip\.part\d+$"
}

if (-not $partFiles) {
    throw "zip part 파일을 찾지 못했습니다: $SourcePartsPath"
}

$groupedArchives = $partFiles |
    Group-Object { Get-ArchiveBaseName -Name $_.Name } |
    Sort-Object Name

$onlyArchives = @(
    $Only |
        ForEach-Object { $_ -split "," } |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ }
)

Write-Host ""
Write-Host "KsponSpeech 데이터 준비" -ForegroundColor Cyan
Write-Host "  원본 part: $SourcePartsPath"
Write-Host "  작업 루트: $WorkingRoot"
Write-Host "  zip 출력:  $zipRoot"
Write-Host "  압축 해제: $extractRoot"
Write-Host "  dry-run:   $DryRun"
Write-Host ""

foreach ($archiveGroup in $groupedArchives) {
    $archiveBaseName = $archiveGroup.Name
    if ($onlyArchives.Count -gt 0 -and ($onlyArchives -notcontains $archiveBaseName)) {
        continue
    }

    $parts = @($archiveGroup.Group | Sort-Object { Get-PartOffset -Name $_.Name })
    $zipPath = Join-Path $zipRoot $archiveBaseName
    $extractTarget = Resolve-ExtractTarget -ArchiveBaseName $archiveBaseName -ExtractRoot $extractRoot

    Write-Host "처리 대상: $archiveBaseName" -ForegroundColor Green
    Write-Host ("  part 수: {0}, 총 용량: {1:N2} GB" -f $parts.Count, (($parts | Measure-Object Length -Sum).Sum / 1GB))

    Join-ArchiveParts -Parts $parts -DestinationPath $zipPath -DryRun:$DryRun -Force:$ForceRebuild

    if (-not $SkipExtract) {
        Expand-KsponArchive -ZipPath $zipPath -DestinationPath $extractTarget -DryRun:$DryRun -Force:$ForceExtract
    }

    Write-Host ""
}

Write-Host "완료되었습니다." -ForegroundColor Cyan
