"""Meeting-minutes PDF writer facade."""

from __future__ import annotations

from pathlib import Path

from server.app.services.reports.composition.pdf_writer.document_reportlab_writer import (
    write_report_document_pdf as write_reportlab_document_pdf,
)
from server.app.services.reports.composition.report_document import ReportDocumentV1


def write_report_document_pdf(
    *,
    output_path: Path,
    document: ReportDocumentV1,
    fallback_lines: list[str],
) -> None:
    """회의록 정본 문서를 표 기반 PDF로 저장한다."""

    _ = fallback_lines
    write_reportlab_document_pdf(output_path=output_path, document=document)
