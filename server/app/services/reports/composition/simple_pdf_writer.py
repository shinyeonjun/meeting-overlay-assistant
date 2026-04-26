"""회의록 PDF writer facade."""

from __future__ import annotations

from pathlib import Path

from server.app.services.reports.composition.html_report_template import ReportDocumentV1
from server.app.services.reports.composition.pdf_writer.document_reportlab_writer import (
    write_report_document_pdf as write_reportlab_document_pdf,
)
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


def write_report_document_pdf(
    *,
    output_path: Path,
    document: ReportDocumentV1,
    fallback_lines: list[str],
) -> None:
    """회의록 정본 문서를 PDF로 저장하고 실패 시 Markdown PDF로 대체한다."""

    try:
        write_reportlab_document_pdf(output_path=output_path, document=document)
        return
    except Exception:
        write_text_pdf(
            output_path=output_path,
            title=document.title,
            lines=fallback_lines,
        )
