"""보고서 스타일 PDF writer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from textwrap import wrap
from xml.sax.saxutils import escape


@dataclass(frozen=True)
class _ReportHeader:
    title: str
    metadata_lines: list[str]
    remaining_lines: list[str]


def write_text_pdf(*, output_path: Path, title: str, lines: list[str]) -> None:
    """Markdown 스타일 라인 목록을 문서형 PDF로 저장한다."""

    try:
        _write_reportlab_pdf(output_path=output_path, title=title, lines=lines)
        return
    except Exception:
        # reportlab 또는 폰트가 준비되지 않은 환경에서는 단순 writer로 fallback 한다.
        _write_fallback_pdf(output_path=output_path, title=title, lines=lines)


def _write_reportlab_pdf(*, output_path: Path, title: str, lines: list[str]) -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

    regular_font_name = "ReportRegular"
    bold_font_name = "ReportBold"
    regular_font_path = Path(r"C:\Windows\Fonts\malgun.ttf")
    bold_font_path = Path(r"C:\Windows\Fonts\malgunbd.ttf")

    if not regular_font_path.exists():
        raise FileNotFoundError("malgun.ttf not found")

    if regular_font_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(regular_font_name, str(regular_font_path)))
    if bold_font_path.exists() and bold_font_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(bold_font_name, str(bold_font_path)))
    if not bold_font_path.exists():
        bold_font_name = regular_font_name

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName=bold_font_name,
        fontSize=24,
        leading=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#111827"),
        spaceAfter=10,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["BodyText"],
        fontName=regular_font_name,
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#6B7280"),
        spaceAfter=6,
    )
    section_style = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        fontName=bold_font_name,
        fontSize=15,
        leading=20,
        textColor=colors.HexColor("#111827"),
        spaceBefore=12,
        spaceAfter=8,
    )
    subsection_style = ParagraphStyle(
        "SubSectionTitle",
        parent=styles["Heading3"],
        fontName=bold_font_name,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1F2937"),
        spaceBefore=8,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontName=regular_font_name,
        fontSize=10.5,
        leading=16,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#1F2937"),
        spaceAfter=4,
    )
    bullet_style = ParagraphStyle(
        "ReportBullet",
        parent=body_style,
        leftIndent=14,
        firstLineIndent=-8,
        bulletIndent=0,
        spaceAfter=4,
    )
    ordered_style = ParagraphStyle(
        "ReportOrdered",
        parent=body_style,
        leftIndent=18,
        firstLineIndent=-12,
        spaceAfter=5,
    )
    meta_style = ParagraphStyle(
        "ReportMeta",
        parent=body_style,
        leftIndent=26,
        textColor=colors.HexColor("#6B7280"),
        fontSize=9.5,
        leading=13,
        spaceAfter=3,
    )
    transcript_style = ParagraphStyle(
        "TranscriptBody",
        parent=body_style,
        leftIndent=12,
        textColor=colors.HexColor("#374151"),
        backColor=colors.HexColor("#F9FAFB"),
        borderPadding=6,
        borderRadius=4,
        spaceAfter=5,
    )

    header = _extract_report_header(lines=lines, fallback_title=title)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    story = [
        Spacer(1, 18),
        Paragraph(escape(header.title), title_style),
        Paragraph(f"생성 시각: {generated_at}", subtitle_style),
    ]
    for meta_line in header.metadata_lines:
        story.append(Paragraph(escape(meta_line.lstrip("- ").strip()), subtitle_style))
    story.extend(
        [
            Spacer(1, 10),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor("#D1D5DB")),
            Spacer(1, 14),
        ]
    )

    in_transcript_section = False
    for raw_line in header.remaining_lines:
        line = raw_line.rstrip()
        if not line:
            story.append(Spacer(1, 4))
            continue

        if line.startswith("## "):
            heading = line[3:].strip()
            story.append(Paragraph(escape(heading), section_style))
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.8,
                    color=colors.HexColor("#E5E7EB"),
                    spaceAfter=8,
                )
            )
            in_transcript_section = heading == "참고 전사"
            continue

        if line.startswith("### "):
            story.append(Paragraph(escape(line[4:].strip()), subsection_style))
            continue

        if line.startswith("  - "):
            story.append(Paragraph(escape(line[4:].strip()), meta_style))
            continue

        if _is_ordered_line(line):
            story.append(Paragraph(escape(line), ordered_style))
            continue

        if line.startswith("- "):
            content = line[2:].strip()
            style = transcript_style if in_transcript_section else bullet_style
            story.append(Paragraph(escape(content), style))
            continue

        story.append(Paragraph(escape(line), body_style))

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
        onFirstPage=_draw_page_chrome,
        onLaterPages=_draw_page_chrome,
    )


def _extract_report_header(*, lines: list[str], fallback_title: str) -> _ReportHeader:
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

    return _ReportHeader(
        title=title,
        metadata_lines=metadata_lines,
        remaining_lines=normalized[index:],
    )


def _draw_page_chrome(canvas, doc) -> None:
    from reportlab.lib import colors

    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#E5E7EB"))
    canvas.line(doc.leftMargin, doc.height + doc.topMargin + 8, doc.pagesize[0] - doc.rightMargin, doc.height + doc.topMargin + 8)
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.drawRightString(
        doc.pagesize[0] - doc.rightMargin,
        24,
        f"{canvas.getPageNumber()}",
    )
    canvas.restoreState()


def _is_ordered_line(line: str) -> bool:
    if ". " not in line:
        return False
    prefix, _ = line.split(". ", 1)
    return prefix.isdigit()


def _wrap_line_for_pdf(
    text: str,
    *,
    font_name: str,
    font_size: int,
    max_width: float,
    fallback_width: int,
) -> list[str]:
    from reportlab.pdfbase import pdfmetrics

    normalized = text.rstrip()
    if not normalized:
        return [""]

    chunks: list[str] = []
    current = ""
    for character in normalized:
        candidate = current + character
        if pdfmetrics.stringWidth(candidate, font_name, font_size) <= max_width:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = character
            continue
        chunks.extend(wrap(normalized, width=fallback_width) or [""])
        return chunks

    if current:
        chunks.append(current)
    return chunks or [""]


def _write_fallback_pdf(*, output_path: Path, title: str, lines: list[str]) -> None:
    sanitized_lines = [title, ""] + [line.rstrip() for line in lines]
    max_lines_per_page = 45
    pages: list[list[str]] = [
        sanitized_lines[index : index + max_lines_per_page]
        for index in range(0, max(len(sanitized_lines), 1), max_lines_per_page)
    ]
    if not pages:
        pages = [[title]]

    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids __KIDS__ /Count __COUNT__ >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    page_obj_ids: list[int] = []
    content_obj_ids: list[int] = []
    next_object_id = 4
    for _ in pages:
        page_obj_ids.append(next_object_id)
        content_obj_ids.append(next_object_id + 1)
        next_object_id += 2

    for page_index, page_lines in enumerate(pages):
        page_obj_id = page_obj_ids[page_index]
        content_obj_id = content_obj_ids[page_index]
        page_object = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_obj_id} 0 R >>"
        ).encode("utf-8")
        objects.append(page_object)

        content_lines = _build_page_content_lines(page_lines)
        content_stream = "\n".join(content_lines).encode("utf-8")
        stream_object = (
            f"<< /Length {len(content_stream)} >>\nstream\n".encode("utf-8")
            + content_stream
            + b"\nendstream"
        )
        objects.append(stream_object)

    kids = " ".join(f"{obj_id} 0 R" for obj_id in page_obj_ids)
    objects[1] = (
        f"<< /Type /Pages /Kids [{kids}] /Count {len(page_obj_ids)} >>"
    ).encode("utf-8")

    pdf_bytes = _build_pdf_bytes(objects)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(pdf_bytes)


def _build_page_content_lines(page_lines: list[str]) -> list[str]:
    lines = ["BT", "/F1 11 Tf", "50 790 Td"]
    for index, line in enumerate(page_lines):
        if index > 0:
            lines.append("0 -16 Td")
        escaped_line = _escape_pdf_text(line)
        lines.append(f"({escaped_line}) Tj")
    lines.append("ET")
    return lines


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_pdf_bytes(objects: list[bytes]) -> bytes:
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    chunks = [header]
    offsets = [0]

    current_offset = len(header)
    for index, obj in enumerate(objects, start=1):
        object_bytes = f"{index} 0 obj\n".encode("utf-8") + obj + b"\nendobj\n"
        offsets.append(current_offset)
        chunks.append(object_bytes)
        current_offset += len(object_bytes)

    xref_offset = current_offset
    xref_lines = [f"xref\n0 {len(offsets)}\n", "0000000000 65535 f \n"]
    xref_lines.extend(f"{offset:010d} 00000 n \n" for offset in offsets[1:])
    xref_bytes = "".join(xref_lines).encode("utf-8")
    chunks.append(xref_bytes)

    trailer = (
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("utf-8")
    chunks.append(trailer)
    return b"".join(chunks)
