"""리포트 영역의 page 서비스를 제공한다."""
from __future__ import annotations


def draw_page_chrome(canvas, doc) -> None:
    """페이지 상단/하단 기본 장식을 그린다."""

    from reportlab.lib import colors

    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#E5E7EB"))
    canvas.line(
        doc.leftMargin,
        doc.height + doc.topMargin + 8,
        doc.pagesize[0] - doc.rightMargin,
        doc.height + doc.topMargin + 8,
    )
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.drawRightString(
        doc.pagesize[0] - doc.rightMargin,
        24,
        f"{canvas.getPageNumber()}",
    )
    canvas.restoreState()


def is_ordered_line(line: str) -> bool:
    """번호 목록 라인인지 확인한다."""

    if ". " not in line:
        return False
    prefix, _ = line.split(". ", 1)
    return prefix.isdigit()
