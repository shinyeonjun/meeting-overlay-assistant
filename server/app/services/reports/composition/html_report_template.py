"""HTML/CSS 기반 회의록 템플릿 렌더러."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from html import escape
from pathlib import Path
from string import Template


TEMPLATE_VERSION = "report_v1"
_TEMPLATE_DIR = Path(__file__).with_name("templates") / TEMPLATE_VERSION


@dataclass(frozen=True)
class ReportMetaField:
    """회의록 상단 메타데이터 항목."""

    label: str
    value: str


@dataclass(frozen=True)
class ReportListItem:
    """회의록 목록형 섹션 항목."""

    text: str
    speaker: str | None = None
    evidence: str | None = None
    time_range: str | None = None


@dataclass(frozen=True)
class ReportActionItem:
    """회의록 액션 아이템 표 항목."""

    task: str
    owner: str = "-"
    due_date: str = "-"
    status: str = "대기"
    note: str | None = None
    time_range: str | None = None


@dataclass(frozen=True)
class ReportDocumentV1:
    """고정 PDF 템플릿에 주입할 회의록 정본 구조."""

    title: str = "회의록"
    metadata: tuple[ReportMetaField, ...] = field(default_factory=tuple)
    summary: tuple[str, ...] = field(default_factory=tuple)
    decisions: tuple[ReportListItem, ...] = field(default_factory=tuple)
    action_items: tuple[ReportActionItem, ...] = field(default_factory=tuple)
    questions: tuple[ReportListItem, ...] = field(default_factory=tuple)
    risks: tuple[ReportListItem, ...] = field(default_factory=tuple)
    transcript_excerpt: tuple[str, ...] = field(default_factory=tuple)
    speaker_insights: tuple[str, ...] = field(default_factory=tuple)


def render_report_html(document: ReportDocumentV1) -> str:
    """회의록 문서를 HTML 문자열로 렌더링한다."""

    template = Template((_TEMPLATE_DIR / "template.html").read_text(encoding="utf-8"))
    stylesheet = (_TEMPLATE_DIR / "styles.css").read_text(encoding="utf-8")
    speaker_insight_section = (
        [_render_numbered_section("발화자 기반 인사이트", document.speaker_insights, compact=True)]
        if document.speaker_insights
        else []
    )
    body = "\n".join(
        [
            '<main class="report-page">',
            _render_cover_header(document),
            _render_metadata_table(document.metadata),
            _render_numbered_section("회의내용", document.summary),
            _render_list_item_section("의결사항", document.decisions),
            _render_action_table(document.action_items),
            _render_list_item_section("질문 및 확인사항", document.questions),
            _render_list_item_section("리스크 및 이슈", document.risks),
            _render_numbered_section("참고 전사", document.transcript_excerpt, compact=True),
            *speaker_insight_section,
            "</main>",
        ]
    )
    return template.substitute(
        document_title=_escape_text(document.title),
        stylesheet=stylesheet,
        body=body,
    )


def report_document_to_dict(document: ReportDocumentV1) -> dict[str, object]:
    """회의록 정본 문서를 artifact로 저장할 수 있는 dict로 변환한다."""

    return {
        "template_version": TEMPLATE_VERSION,
        "document": asdict(document),
    }


def build_sample_report_document() -> ReportDocumentV1:
    """디자인 확인용 샘플 문서를 만든다."""

    return ReportDocumentV1(
        metadata=(
            ReportMetaField("회의일자", "2026-04-25"),
            ReportMetaField("회의시간", "10:00 - 10:45"),
            ReportMetaField("회의장소", "온라인 회의실"),
            ReportMetaField("회의주제", "CAPS 회의록 품질 개선 회의"),
            ReportMetaField("회의안건", "PDF 템플릿 고정 및 회의록 구조화"),
            ReportMetaField("참석자", "진행자, 개발자, 회의 정리 담당자"),
        ),
        summary=(
            "PDF 레이아웃은 고정 템플릿으로 관리하고, LLM은 섹션 내용을 채우는 역할로 제한한다.",
            "회의록 정본은 PDF 파일이 아니라 ReportDocumentV1 구조로 관리한다.",
            "생성된 PDF와 Markdown은 artifact로 저장하고, 템플릿은 코드 저장소에서 버전 관리한다.",
        ),
        decisions=(
            ReportListItem(
                "회의록 PDF는 회색 섹션 바와 표 기반의 단정한 문서형 템플릿을 기본으로 한다.",
                evidence="회의 후 검수와 공유가 쉬운 형태가 우선이다.",
                time_range="00:03-00:18",
            ),
            ReportListItem(
                "추후 HTML/CSS 렌더러를 PDF 생성 파이프라인에 연결한다.",
                evidence="현재는 ReportLab fallback이 존재한다.",
                time_range="00:19-00:36",
            ),
        ),
        action_items=(
            ReportActionItem(
                task="ReportDocumentV1과 기존 Markdown 회의록 사이 변환 계층 설계",
                owner="CAPS",
                due_date="다음 차수",
                status="대기",
                time_range="00:37-00:52",
            ),
            ReportActionItem(
                task="HTML/CSS 템플릿을 PDF 렌더러에 연결하는 후보 검증",
                owner="CAPS",
                due_date="다음 차수",
                status="대기",
                note="Windows 로컬 의존성 부담을 같이 확인한다.",
                time_range="00:53-01:08",
            ),
        ),
        questions=(
            ReportListItem("workspace별 로고와 색상 커스텀은 언제부터 필요한가?"),
            ReportListItem("appendix transcript는 전체 원문과 주요 발화 중 무엇을 기본으로 할 것인가?"),
        ),
        risks=(
            ReportListItem("LLM이 임의로 문서 구조를 바꾸면 회의록 품질이 흔들릴 수 있다."),
        ),
        transcript_excerpt=(
            "[SPEAKER_00] PDF 모양은 고정하고 내용만 채우는 방식이 맞습니다.",
            "[SPEAKER_01] 템플릿은 repo에서 관리하고 생성된 PDF만 artifact로 저장합시다.",
        ),
    )


def render_sample_report_html() -> str:
    """디자인 확인용 샘플 HTML을 렌더링한다."""

    return render_report_html(build_sample_report_document())


def _render_cover_header(document: ReportDocumentV1) -> str:
    return "\n".join(
        [
            '<header class="report-header">',
            f'<p class="report-kicker">CAPS MEETING REPORT</p>',
            f"<h1>{_escape_text(document.title)}</h1>",
            "</header>",
        ]
    )


def _render_metadata_table(fields: tuple[ReportMetaField, ...]) -> str:
    if not fields:
        fields = (ReportMetaField("회의정보", "-"),)

    rows: list[str] = []
    for index in range(0, len(fields), 2):
        first = fields[index]
        second = fields[index + 1] if index + 1 < len(fields) else None
        second_cells = (
            f"<th>{_escape_text(second.label)}</th><td>{_escape_text(second.value)}</td>"
            if second is not None
            else '<th class="empty-cell"></th><td class="empty-cell"></td>'
        )
        rows.append(
            "<tr>"
            f"<th>{_escape_text(first.label)}</th><td>{_escape_text(first.value)}</td>"
            f"{second_cells}"
            "</tr>"
        )

    return "\n".join(
        [
            '<section class="metadata-section">',
            '<table class="metadata-table">',
            "<tbody>",
            *rows,
            "</tbody>",
            "</table>",
            "</section>",
        ]
    )


def _render_numbered_section(
    title: str,
    items: tuple[str, ...],
    *,
    compact: bool = False,
) -> str:
    section_class = "report-section compact" if compact else "report-section"
    if not items:
        item_html = '<p class="empty-state">기록된 내용이 없습니다.</p>'
    else:
        item_html = "\n".join(
            [
                '<ol class="numbered-list">',
                *[f"<li>{_escape_multiline(item)}</li>" for item in items],
                "</ol>",
            ]
        )
    return "\n".join(
        [
            f'<section class="{section_class}">',
            f'<h2 class="section-title">{_escape_text(title)}</h2>',
            item_html,
            "</section>",
        ]
    )


def _render_list_item_section(title: str, items: tuple[ReportListItem, ...]) -> str:
    if not items:
        item_html = '<p class="empty-state">기록된 내용이 없습니다.</p>'
    else:
        rendered_items = []
        for item in items:
            meta_parts = []
            if item.speaker:
                meta_parts.append(f"발화자: {_escape_text(item.speaker)}")
            if item.time_range:
                meta_parts.append(f"근거 구간: {_escape_text(item.time_range)}")
            if item.evidence:
                meta_parts.append(f"근거: {_escape_text(item.evidence)}")
            meta_html = (
                f'<p class="item-evidence">{" · ".join(meta_parts)}</p>' if meta_parts else ""
            )
            rendered_items.append(
                "<li>"
                f'<span class="item-text">{_escape_multiline(item.text)}</span>'
                f"{meta_html}"
                "</li>"
            )
        item_html = "\n".join(['<ol class="numbered-list">', *rendered_items, "</ol>"])

    return "\n".join(
        [
            '<section class="report-section">',
            f'<h2 class="section-title">{_escape_text(title)}</h2>',
            item_html,
            "</section>",
        ]
    )


def _render_action_table(items: tuple[ReportActionItem, ...]) -> str:
    if not items:
        rows = ['<tr><td colspan="5" class="empty-state table-empty">기록된 액션 아이템이 없습니다.</td></tr>']
    else:
        rows = []
        for item in items:
            note_parts = []
            if item.time_range:
                note_parts.append(f"근거 구간: {item.time_range}")
            if item.note:
                note_parts.append(item.note)
            note_text = "\n".join(note_parts) if note_parts else "-"
            rows.append(
                "<tr>"
                f"<td>{_escape_multiline(item.task)}</td>"
                f"<td>{_escape_text(item.owner)}</td>"
                f"<td>{_escape_text(item.due_date)}</td>"
                f"<td>{_escape_text(item.status)}</td>"
                f"<td>{_escape_multiline(note_text)}</td>"
                "</tr>"
            )

    return "\n".join(
        [
            '<section class="report-section">',
            '<h2 class="section-title">회의결과</h2>',
            '<table class="action-table">',
            "<thead>",
            "<tr><th>부서 및 작업</th><th>담당자</th><th>기한</th><th>상태</th><th>비고</th></tr>",
            "</thead>",
            "<tbody>",
            *rows,
            "</tbody>",
            "</table>",
            "</section>",
        ]
    )


def _escape_text(value: str) -> str:
    return escape(value, quote=True)


def _escape_multiline(value: str) -> str:
    return _escape_text(value).replace("\n", "<br>")
