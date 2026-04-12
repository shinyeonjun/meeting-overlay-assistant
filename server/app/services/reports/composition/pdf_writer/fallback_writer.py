"""간단한 텍스트 기반 fallback PDF writer."""

from __future__ import annotations

from pathlib import Path


def write_fallback_pdf(*, output_path: Path, title: str, lines: list[str]) -> None:
    """ReportLab이 없을 때 단순 PDF를 생성한다."""

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
        content_obj_id = content_obj_ids[page_index]
        page_object = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_obj_id} 0 R >>"
        ).encode("utf-8")
        objects.append(page_object)

        content_lines = build_page_content_lines(page_lines)
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

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(build_pdf_bytes(objects))


def build_page_content_lines(page_lines: list[str]) -> list[str]:
    """페이지별 PDF 텍스트 스트림을 만든다."""

    lines = ["BT", "/F1 11 Tf", "50 790 Td"]
    for index, line in enumerate(page_lines):
        if index > 0:
            lines.append("0 -16 Td")
        escaped_line = escape_pdf_text(line)
        lines.append(f"({escaped_line}) Tj")
    lines.append("ET")
    return lines


def escape_pdf_text(text: str) -> str:
    """PDF 텍스트 스트림용 이스케이프를 적용한다."""

    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf_bytes(objects: list[bytes]) -> bytes:
    """PDF object 목록으로 최종 바이트를 조립한다."""

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
    chunks.append("".join(xref_lines).encode("utf-8"))
    chunks.append(
        (
            f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("utf-8")
    )
    return b"".join(chunks)

