"""회의록 정본 PDF writer 테스트."""

from pathlib import Path

import pytest

from server.app.services.reports.composition.html_report_template import (
    ReportActionItem,
    ReportDocumentV1,
    ReportListItem,
    ReportMetaField,
)
from server.app.services.reports.composition.pdf_writer.document_reportlab_writer import (
    write_report_document_pdf,
)


def test_report_document_pdf_writer가_정본_회의록_pdf를_생성한다(tmp_path: Path) -> None:
    document = ReportDocumentV1(
        metadata=(
            ReportMetaField("회의일자", "2026-04-25"),
            ReportMetaField("회의주제", "릴리즈 점검"),
            ReportMetaField("참석자", "민수, 지현"),
        ),
        summary=("회의록 PDF는 정본 데이터를 기준으로 생성한다.",),
        decisions=(
            ReportListItem(
                "PDF 다운로드를 MVP에 포함한다.",
                evidence="공유 가능한 결과물이 필요하다.",
                time_range="00:01-00:05",
            ),
        ),
        action_items=(
            ReportActionItem(
                task="PDF 다운로드 회귀 테스트 추가",
                owner="CAPS",
                status="완료",
                time_range="00:06-00:10",
            ),
        ),
        transcript_excerpt=("[SPEAKER_00] PDF로 내려받을 수 있어야 합니다.",),
    )
    output_path = tmp_path / "meeting-minutes.pdf"

    write_report_document_pdf(output_path=output_path, document=document)

    assert output_path.exists()
    assert output_path.read_bytes().startswith(b"%PDF")
    assert output_path.stat().st_size > 20_000


def test_report_document_pdf_writer가_pdf_텍스트를_추출할_수_있게_쓴다(
    tmp_path: Path,
) -> None:
    pypdf = pytest.importorskip("pypdf")
    document = ReportDocumentV1(
        metadata=(ReportMetaField("회의주제", "PDF 다운로드 검증"),),
        summary=("회의내용이 PDF 본문에 들어간다.",),
        decisions=(ReportListItem("정본 기반 PDF writer를 사용한다."),),
    )
    output_path = tmp_path / "extractable.pdf"

    write_report_document_pdf(output_path=output_path, document=document)

    reader = pypdf.PdfReader(str(output_path))
    extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "CAPS MEETING REPORT" in extracted_text
    assert "회의록" in extracted_text
    assert "PDF 다운로드 검증" in extracted_text
    assert "회의내용" in extracted_text
    assert "정본 기반 PDF writer를 사용한다" in extracted_text
