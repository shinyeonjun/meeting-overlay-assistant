"""회의록 정본 PDF writer 테스트."""

from pathlib import Path

import pytest

from server.app.services.reports.composition.report_document import (
    ReportActionItem,
    ReportDocumentV1,
    ReportListItem,
    ReportMetaField,
    ReportSection,
)
from server.app.services.reports.composition.pdf_writer.document_reportlab_writer import (
    write_report_document_pdf,
)
from server.app.services.reports.composition.pdf_writer.reportlab_helpers import (
    build_report_story,
    build_report_styles,
)


def test_report_document_pdf_writer가_정본_회의록_pdf를_생성한다(tmp_path: Path) -> None:
    document = ReportDocumentV1(
        metadata=(
            ReportMetaField("회의제목", "릴리즈 점검"),
            ReportMetaField("일시", "2026-04-25 10:00 - 10:45"),
            ReportMetaField("장소", "온라인"),
            ReportMetaField("작성자", "제품팀"),
            ReportMetaField("작성일", "2026-04-25"),
            ReportMetaField("참석자", "민수, 지현"),
        ),
        summary=("회의록 PDF는 정본 데이터를 기준으로 생성한다.",),
        sections=(
            ReportSection(
                title="PDF 다운로드",
                discussion=(
                    ReportListItem(
                        "PDF 다운로드는 공유 가능한 결과물 흐름에서 확인한다.",
                        time_range="00:01-00:05",
                    ),
                ),
            ),
        ),
        agenda=(
            ReportListItem(
                "PDF 다운로드를 결과물 흐름에서 확인했다.",
                time_range="00:00-00:01",
            ),
        ),
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
        metadata=(
            ReportMetaField("일시", "2026-04-25 10:00 - 10:45"),
            ReportMetaField("작성자", "CAPS"),
        ),
        summary=("회의 요약이 PDF 본문에 들어간다.",),
        agenda=(ReportListItem("PDF 다운로드 검증"),),
        discussion=(ReportListItem("다운로드 결과물 구조를 점검한다."),),
        decisions=(ReportListItem("정본 기반 PDF writer를 사용한다."),),
    )
    output_path = tmp_path / "extractable.pdf"

    write_report_document_pdf(output_path=output_path, document=document)

    reader = pypdf.PdfReader(str(output_path))
    extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "회의록" in extracted_text
    assert "PDF 다운로드 검증" in extracted_text
    assert "회의 요약" not in extracted_text
    assert "안건" in extracted_text
    assert "회의내용" in extracted_text
    assert "결정사항" in extracted_text
    assert "특이사항" in extracted_text
    assert "향후일정" in extracted_text
    assert "다운로드 결과물 구조를 점검한다" in extracted_text
    assert "정본 기반 PDF writer를 사용한다" in extracted_text


def test_markdown_pdf_writer는_헤더에_생성시각과_세션_id를_표시하지_않는다(
) -> None:
    _, story = build_report_story(
        title="회의록",
        lines=[
            "# 회의록",
            "",
            "- 세션 ID: session-doc",
            "",
            "## 회의내용",
            "- PDF 헤더 표시 정책을 확인한다.",
        ],
        styles=build_report_styles(),
    )

    story_text = "\n".join(
        item.getPlainText()
        for item in story
        if hasattr(item, "getPlainText")
    )
    assert "회의록" in story_text
    assert "PDF 헤더 표시 정책을 확인한다" in story_text
    assert "생성 시각" not in story_text
    assert "세션 ID" not in story_text


def test_report_document_pdf_writer가_계층형_논의내용을_쓴다(
    tmp_path: Path,
) -> None:
    pypdf = pytest.importorskip("pypdf")
    document = ReportDocumentV1(
        metadata=(ReportMetaField("회의제목", "계층형 회의록"),),
        sections=(
            ReportSection(
                title="회의록 구조",
                background=(
                    ReportListItem("기존 회의내용이 단순 목록으로 표시되어 구조 개선이 필요했다."),
                ),
                opinions=(
                    ReportListItem("소주제 아래 논의 항목을 묶어서 표시하자는 의견이 나왔다."),
                ),
                review=(
                    ReportListItem("결정사항과 향후일정은 회의내용과 분리해 표시하기로 검토했다."),
                ),
                direction=(
                    ReportListItem("회의내용은 소주제별 구조화 항목으로 표시한다."),
                ),
            ),
        ),
        agenda=(ReportListItem("회의록 구조"),),
        decisions=(ReportListItem("legacy 결정 fallback은 쓰지 않는다."),),
    )
    output_path = tmp_path / "sectioned.pdf"

    write_report_document_pdf(output_path=output_path, document=document)

    reader = pypdf.PdfReader(str(output_path))
    extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "회의록 구조" in extracted_text
    assert "논의 배경" in extracted_text
    assert "주요 의견" in extracted_text
    assert "검토 내용" in extracted_text
    assert "정리된 방향" in extracted_text
    assert "회의내용은 소주제별 구조화 항목으로 표시한다" in extracted_text
    assert "legacy 결정 fallback은 쓰지 않는다" in extracted_text
    assert "근거 구간" not in extracted_text
