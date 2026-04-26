"""HTML 회의록 템플릿 테스트."""

from server.app.services.reports.composition.html_report_template import (
    ReportActionItem,
    ReportDocumentV1,
    ReportListItem,
    ReportMetaField,
    render_report_html,
    render_sample_report_html,
    report_document_to_dict,
)


def test_render_report_html이_고정_회의록_섹션을_렌더링한다() -> None:
    document = ReportDocumentV1(
        metadata=(
            ReportMetaField("회의일자", "2026-04-25"),
            ReportMetaField("회의주제", "PDF 템플릿 확정"),
        ),
        summary=("PDF 모양은 고정하고 내용만 채운다.",),
        decisions=(
            ReportListItem(
                "ReportDocumentV1을 정본 구조로 둔다.",
                time_range="00:12-00:30",
            ),
        ),
        action_items=(
            ReportActionItem(
                task="HTML 템플릿 초안 생성",
                owner="CAPS",
                due_date="오늘",
                status="완료",
                time_range="00:31-00:45",
            ),
        ),
    )

    html = render_report_html(document)

    assert "<!doctype html>" in html
    assert "CAPS MEETING REPORT" in html
    assert "회의일자" in html
    assert "회의내용" in html
    assert "의결사항" in html
    assert "회의결과" in html
    assert "근거 구간: 00:12-00:30" in html
    assert "근거 구간: 00:31-00:45" in html
    assert "HTML 템플릿 초안 생성" in html


def test_render_report_html이_사용자_텍스트를_이스케이프한다() -> None:
    document = ReportDocumentV1(
        metadata=(ReportMetaField("회의주제", "<script>alert(1)</script>"),),
        summary=("A&B < C",),
    )

    html = render_report_html(document)

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "A&amp;B &lt; C" in html


def test_render_sample_report_html이_미리보기_문서를_렌더링한다() -> None:
    html = render_sample_report_html()

    assert "CAPS 리포트 품질 개선 회의" in html
    assert "ReportDocumentV1" in html
    assert "workspace별 로고" in html


def test_report_document_to_dict가_템플릿_버전과_정본을_보존한다() -> None:
    document = ReportDocumentV1(
        metadata=(ReportMetaField("회의주제", "릴리즈 점검"),),
        summary=("회의록 정본을 저장한다.",),
    )

    payload = report_document_to_dict(document)

    assert payload["template_version"] == "report_v1"
    assert payload["document"]["metadata"][0]["label"] == "회의주제"
    assert payload["document"]["summary"] == ("회의록 정본을 저장한다.",)
    assert payload["document"]["metadata"][0]["value"] == "릴리즈 점검"
