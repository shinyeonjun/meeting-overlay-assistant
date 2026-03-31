"""ReportLab 기반 PDF writer."""

from __future__ import annotations

from pathlib import Path

from server.app.services.reports.composition.pdf_writer.reportlab_helpers import (
    build_report_story,
    build_report_styles,
    draw_page_chrome,
)


def write_reportlab_pdf(*, output_path: Path, title: str, lines: list[str]) -> None:
    """ReportLab으로 PDF를 생성한다."""

    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate

    styles = build_report_styles()
    header, story = build_report_story(title=title, lines=lines, styles=styles)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=48,
        rightMargin=48,
        topMargin=42,
        bottomMargin=42,
        title=header.title,
        author="Meeting Overlay Assistant",
    )
    doc.build(
        story,
        onFirstPage=draw_page_chrome,
        onLaterPages=draw_page_chrome,
    )
