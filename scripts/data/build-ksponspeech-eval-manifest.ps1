param(
    [string]$KsponRoot = "D:\stt_data\fine_tuning\extracted\ksponspeech",
    [string]$OutputPath = "D:\stt_data\fine_tuning\eval_sets\public_baseline\ksponspeech_eval_manifest.jsonl",
    [switch]$DryRun
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

function Convert-KsponReferenceToDisplayText {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Text
    )

    $normalized = $Text.Trim()

    # 발화 주석 marker 제거: o/, b/, l/, u/, n/ 등
    $normalized = [regex]::Replace($normalized, "(?<!\S)[a-zA-Z]\/\s*", "")
    # hesitation/연장 marker 제거
    $normalized = $normalized -replace "\+", ""
    # 이중 표기 (표기)/(발화) 는 발화형(두 번째)을 우선 채택
    $normalized = [regex]::Replace(
        $normalized,
        "\(([^()]+)\)\/\(([^()]+)\)",
        { param($m) $m.Groups[2].Value }
    )
    # 남은 중복 공백 정리
    $normalized = [regex]::Replace($normalized, "\s+", " ").Trim()
    return $normalized
}

function Parse-KsponTranscriptLine {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Line
    )

    $parts = $Line -split "\s+::\s+", 2
    if ($parts.Count -ne 2) {
        throw "KsponSpeech 전사 형식을 해석할 수 없습니다: $Line"
    }

    $relativePath = $parts[0].Trim()
    $referenceRaw = $parts[1].Trim()
    return [PSCustomObject]@{
        RelativePath = $relativePath
        ReferenceRaw = $referenceRaw
        ReferenceDisplay = Convert-KsponReferenceToDisplayText -Text $referenceRaw
    }
}

function Build-KsponManifestEntries {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TranscriptPath,
        [Parameter(Mandatory = $true)]
        [string]$KsponRoot
    )

    $splitName = [System.IO.Path]::GetFileNameWithoutExtension($TranscriptPath)
    foreach ($line in Get-Content -LiteralPath $TranscriptPath -Encoding UTF8) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        $parsed = Parse-KsponTranscriptLine -Line $line
        $resolvedRelativePath = $parsed.RelativePath
        if ($resolvedRelativePath.StartsWith("KsponSpeech_eval/")) {
            $resolvedRelativePath = $resolvedRelativePath -replace "^KsponSpeech_eval/", "eval/"
        } elseif ($resolvedRelativePath.StartsWith("KsponSpeech_01/")) {
            $resolvedRelativePath = $resolvedRelativePath -replace "^KsponSpeech_01/", "train/"
        } elseif ($resolvedRelativePath.StartsWith("KsponSpeech_02/")) {
            $resolvedRelativePath = $resolvedRelativePath -replace "^KsponSpeech_02/", "train/"
        } elseif ($resolvedRelativePath.StartsWith("KsponSpeech_03/")) {
            $resolvedRelativePath = $resolvedRelativePath -replace "^KsponSpeech_03/", "train/"
        } elseif ($resolvedRelativePath.StartsWith("KsponSpeech_04/")) {
            $resolvedRelativePath = $resolvedRelativePath -replace "^KsponSpeech_04/", "train/"
        } elseif ($resolvedRelativePath.StartsWith("KsponSpeech_05/")) {
            $resolvedRelativePath = $resolvedRelativePath -replace "^KsponSpeech_05/", "train/"
        }

        $audioPath = Join-Path $KsponRoot $resolvedRelativePath
        if (-not (Test-Path -LiteralPath $audioPath)) {
            throw "오디오 파일을 찾을 수 없습니다: $audioPath"
        }

        [PSCustomObject]@{
            dataset = "ksponspeech"
            split = $splitName
            audio_path = $audioPath
            audio_format = [System.IO.Path]::GetExtension($audioPath).TrimStart(".").ToLowerInvariant()
            relative_path = $resolvedRelativePath
            source_relative_path = $parsed.RelativePath
            reference_raw = $parsed.ReferenceRaw
            reference_display = $parsed.ReferenceDisplay
        }
    }
}

$scriptsPath = Join-Path $KsponRoot "scripts"
if (-not (Test-Path -LiteralPath $scriptsPath)) {
    throw "KsponSpeech scripts 폴더를 찾을 수 없습니다: $scriptsPath"
}

$transcriptFiles = @(
    Join-Path $scriptsPath "eval_clean.trn"
    Join-Path $scriptsPath "eval_other.trn"
)

foreach ($transcriptFile in $transcriptFiles) {
    if (-not (Test-Path -LiteralPath $transcriptFile)) {
        throw "전사 파일을 찾을 수 없습니다: $transcriptFile"
    }
}

$allEntries = foreach ($transcriptFile in $transcriptFiles) {
    Build-KsponManifestEntries -TranscriptPath $transcriptFile -KsponRoot $KsponRoot
}

$outputDirectory = Split-Path -Parent $OutputPath
Ensure-Directory -Path $outputDirectory

Write-Host ""
Write-Host "KsponSpeech eval manifest 생성" -ForegroundColor Cyan
Write-Host "  입력 루트: $KsponRoot"
Write-Host "  출력 파일: $OutputPath"
Write-Host "  총 항목 수: $($allEntries.Count)"
Write-Host "  dry-run:   $DryRun"
Write-Host ""

if ($DryRun) {
    $allEntries | Select-Object -First 5 | ConvertTo-Json -Depth 4
    return
}

$utf8Bom = New-Object System.Text.UTF8Encoding($true)
$writer = New-Object System.IO.StreamWriter($OutputPath, $false, $utf8Bom)
try {
    foreach ($entry in $allEntries) {
        $writer.WriteLine(($entry | ConvertTo-Json -Compress -Depth 4))
    }
} finally {
    $writer.Dispose()
}

Write-Host "manifest 생성 완료" -ForegroundColor Green
