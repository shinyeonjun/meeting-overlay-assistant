"""간단한 텍스트 기반 PDF writer."""

from __future__ import annotations

from pathlib import Path
from textwrap import wrap


def write_text_pdf(*, output_path: Path, title: str, lines: list[str]) -> None:
    """텍스트 라인 목록을 PDF 파일로 저장한다."""

    try:
        _write_reportlab_pdf(output_path=output_path, title=title, lines=lines)
        return
    except Exception:
        # reportlab 또는 폰트가 준비되지 않은 환경에서는 단순 writer로 fallback 한다.
        _write_fallback_pdf(output_path=output_path, title=title, lines=lines)


def _write_reportlab_pdf(*, output_path: Path, title: str, lines: list[str]) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

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

    page_width, page_height = A4
    margin_x = 48
    margin_top = 56
    margin_bottom = 44
    title_font = bold_font_name if bold_font_path.exists() else regular_font_name
    title_font_size = 16
    body_font_size = 10
    line_gap = 14
    max_text_width = page_width - (margin_x * 2)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(output_path), pagesize=A4)

    def start_page() -> float:
        pdf.setFont(title_font, title_font_size)
        pdf.drawString(margin_x, page_height - margin_top, title)
        pdf.setFont(regular_font_name, body_font_size)
        return page_height - margin_top - 28

    current_y = start_page()
    for raw_line in lines:
        wrapped_lines = _wrap_line_for_pdf(
            raw_line,
            font_name=regular_font_name,
            font_size=body_font_size,
            max_width=max_text_width,
            fallback_width=68,
        )
        for wrapped_line in wrapped_lines:
            if current_y <= margin_bottom:
                pdf.showPage()
                current_y = start_page()
            pdf.drawString(margin_x, current_y, wrapped_line)
            current_y -= line_gap

    pdf.save()


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
