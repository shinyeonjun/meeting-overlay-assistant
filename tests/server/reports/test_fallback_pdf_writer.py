"""Fallback PDF writer 테스트."""

from __future__ import annotations

from pathlib import Path

from server.app.services.reports.composition.pdf_writer.fallback_writer import (
    build_pdf_bytes,
    escape_pdf_text,
    write_fallback_pdf,
)


def test_escape_pdf_text가_특수문자를_이스케이프한다() -> None:
    assert escape_pdf_text(r"(sample)\path") == r"\(sample\)\\path"


def test_write_fallback_pdf가_pdf파일을_생성한다(tmp_path: Path) -> None:
    output_path = tmp_path / "fallback.pdf"

    write_fallback_pdf(
        output_path=output_path,
        title="Fallback Report",
        lines=["line 1", "line (2) \\ sample"],
    )

    pdf_bytes = output_path.read_bytes()
    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert b"Fallback Report" in pdf_bytes
    assert b"line \\(2\\) \\\\ sample" in pdf_bytes


def test_build_pdf_bytes가_여러_페이지_object를_조립한다() -> None:
    pdf_bytes = build_pdf_bytes(
        [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [4 0 R 6 0 R] /Count 2 >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Type /Page /Parent 2 0 R /Contents 5 0 R >>",
            b"<< /Length 0 >>\nstream\n\nendstream",
            b"<< /Type /Page /Parent 2 0 R /Contents 7 0 R >>",
            b"<< /Length 0 >>\nstream\n\nendstream",
        ]
    )

    assert b"/Count 2" in pdf_bytes
    assert b"xref" in pdf_bytes
