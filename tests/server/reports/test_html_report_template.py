"""HTML 회의록 템플릿 테스트."""

from server.app.services.reports.composition.report_document import (
    ReportActionItem,
    ReportDocumentV1,
    ReportListItem,
    ReportMetaField,
    ReportSection,
    report_document_to_dict,
)
from server.app.services.reports.composition.html_report_template import (
    render_report_html,
    render_sample_report_html,
)
from server.app.services.reports.composition.report_markdown_renderer import (
    render_report_markdown,
)


def test_render_report_html이_고정_회의록_섹션을_렌더링한다() -> None:
    document = ReportDocumentV1(
        metadata=(
            ReportMetaField("회의제목", "PDF 템플릿 확정"),
            ReportMetaField("일시", "2026-04-25 10:00 - 10:45"),
            ReportMetaField("장소", "온라인"),
            ReportMetaField("작성자", "제품팀"),
            ReportMetaField("작성일", "2026-04-25"),
            ReportMetaField("참석자", "CAPS"),
        ),
        summary=("PDF 모양은 고정하고 내용만 채운다.",),
        sections=(
            ReportSection(
                title="PDF 템플릿",
                time_range="00:01-00:30",
                background=(
                    ReportListItem("공유 가능한 결과물을 만들기 위해 PDF 템플릿을 점검했다."),
                ),
                opinions=(
                    ReportListItem("PDF 템플릿은 고정 양식을 우선 사용한다는 의견이 나왔다."),
                ),
                review=(
                    ReportListItem("HTML과 PDF가 같은 정본 데이터를 쓰는지 확인했다."),
                ),
                direction=(
                    ReportListItem("ReportDocumentV1을 기준으로 HTML과 PDF를 함께 생성한다."),
                ),
            ),
        ),
        agenda=(
            ReportListItem(
                "PDF 템플릿 고정 방향을 논의했다.",
                time_range="00:01-00:11",
            ),
        ),
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
    assert "회의록" in html
    assert "회의개요" in html
    assert "일시" in html
    assert "장소" in html
    assert "작성자" in html
    assert "작성일" in html
    assert "참석자" in html
    assert "회의 요약" not in html
    assert "안건" in html
    assert "회의내용" in html
    assert "결정사항" in html
    assert "특이사항" in html
    assert "향후일정" in html
    assert "작성자: CAPS" not in html
    assert "PDF 템플릿 고정 방향을 논의했다." in html
    assert "논의 배경" in html
    assert "주요 의견" in html
    assert "검토 내용" in html
    assert "정리된 방향" in html
    assert "PDF 템플릿은 고정 양식을 우선 사용한다는 의견이 나왔다." in html
    assert "근거 구간" not in html
    assert "근거:" not in html
    assert "HTML 템플릿 초안 생성" in html


def test_render_report_html이_사용자_텍스트를_이스케이프한다() -> None:
    document = ReportDocumentV1(
        metadata=(ReportMetaField("작성자", "<script>alert(1)</script>"),),
        agenda=(ReportListItem("A&B < C"),),
    )

    html = render_report_html(document)

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "A&amp;B &lt; C" in html


def test_renderers는_섹션_논의가_없으면_평면_결정_fallback을_사용한다() -> None:
    document = ReportDocumentV1(
        metadata=(ReportMetaField("회의제목", "fallback 검증"),),
        sections=(ReportSection("안건만 있는 섹션"),),
        decisions=(ReportListItem("정본 기반 PDF writer를 사용한다."),),
    )

    html = render_report_html(document)
    markdown = render_report_markdown(session_id="session-doc", document=document)

    assert "결정사항" in html
    assert "정본 기반 PDF writer를 사용한다." in html
    assert "## 결정사항" in markdown
    assert "1. 정본 기반 PDF writer를 사용한다." in markdown


def test_renderers는_섹션_하위_특이사항과_추후일정을_사용한다() -> None:
    document = ReportDocumentV1(
        metadata=(ReportMetaField("회의제목", "섹션 하위 필드"),),
        sections=(
            ReportSection(
                title="품질 점검",
                special_notes=(ReportListItem("외부 공유 전 민감정보를 확인해야 한다."),),
                action_items=(
                    ReportActionItem(
                        task="PDF 다운로드 결과를 다시 확인한다.",
                        owner="CAPS",
                    ),
                ),
            ),
        ),
    )

    html = render_report_html(document)
    markdown = render_report_markdown(session_id="session-doc", document=document)

    assert "외부 공유 전 민감정보를 확인해야 한다." in html
    assert "PDF 다운로드 결과를 다시 확인한다." in html
    assert "1. 외부 공유 전 민감정보를 확인해야 한다." in markdown
    assert "- [ ] PDF 다운로드 결과를 다시 확인한다." in markdown


def test_render_sample_report_html이_미리보기_문서를_렌더링한다() -> None:
    html = render_sample_report_html()

    assert "고객중심과 외부지향 회사전략에 대한 인식제고" in html
    assert "현재 회사전략에 대한 사원들의 이해도 점검" in html
    assert "회의내용" in html


def test_report_document_to_dict가_템플릿_버전과_정본을_보존한다() -> None:
    document = ReportDocumentV1(
        metadata=(ReportMetaField("회의제목", "릴리즈 점검"),),
        summary=("회의록 정본을 저장한다.",),
        sections=(ReportSection("배포 범위"),),
    )

    payload = report_document_to_dict(document)

    assert payload["template_version"] == "report_v1"
    assert payload["document"]["metadata"][0]["label"] == "회의제목"
    assert payload["document"]["summary"] == ("회의록 정본을 저장한다.",)
    assert payload["document"]["sections"][0]["title"] == "배포 범위"
    assert payload["document"]["metadata"][0]["value"] == "릴리즈 점검"
