"""리포트 영역의 header 서비스를 제공한다."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReportHeader:
    """PDF 렌더링용 헤더 정보."""

    title: str
    metadata_lines: list[str]
    remaining_lines: list[str]


def extract_report_header(*, lines: list[str], fallback_title: str) -> ReportHeader:
    """Markdown 라인에서 보고서 헤더를 추출한다."""

    normalized = [line.rstrip() for line in lines]
    title = fallback_title
    metadata_lines: list[str] = []
    index = 0

    while index < len(normalized) and not normalized[index]:
        index += 1

    if index < len(normalized) and normalized[index].startswith("# "):
        title = normalized[index][2:].strip() or fallback_title
        index += 1

    while index < len(normalized):
        line = normalized[index]
        if not line:
            index += 1
            continue
        if line.startswith("## "):
            break
        if line.startswith("- "):
            metadata_lines.append(line)
        index += 1

    return ReportHeader(
        title=title,
        metadata_lines=metadata_lines,
        remaining_lines=normalized[index:],
    )

