"""보고서용 간단한 PDF writer facade."""

from __future__ import annotations

from pathlib import Path

from server.app.services.reports.composition.pdf_writer.fallback_writer import (
    write_fallback_pdf,
)
from server.app.services.reports.composition.pdf_writer.reportlab_writer import (
    write_reportlab_pdf,
)


def write_text_pdf(*, output_path: Path, title: str, lines: list[str]) -> None:
    """Markdown 라인 목록을 PDF 문서로 저장한다."""

    try:
        write_reportlab_pdf(output_path=output_path, title=title, lines=lines)
        return
    except Exception:
        # reportlab이나 폰트가 없는 환경에서는 단순 writer로 fallback 한다.
        write_fallback_pdf(output_path=output_path, title=title, lines=lines)
