"""회의록 HTML/PDF/Markdown 렌더러가 공유하는 정본 문서 모델."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


REPORT_DOCUMENT_VERSION = "report_v1"


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
    """회의록 생성 파이프라인의 정본 구조."""

    title: str = "회의록"
    metadata: tuple[ReportMetaField, ...] = field(default_factory=tuple)
    summary: tuple[str, ...] = field(default_factory=tuple)
    agenda: tuple[ReportListItem, ...] = field(default_factory=tuple)
    decisions: tuple[ReportListItem, ...] = field(default_factory=tuple)
    action_items: tuple[ReportActionItem, ...] = field(default_factory=tuple)
    questions: tuple[ReportListItem, ...] = field(default_factory=tuple)
    risks: tuple[ReportListItem, ...] = field(default_factory=tuple)
    transcript_excerpt: tuple[str, ...] = field(default_factory=tuple)
    speaker_insights: tuple[str, ...] = field(default_factory=tuple)


def report_document_to_dict(document: ReportDocumentV1) -> dict[str, object]:
    """회의록 정본 문서를 artifact로 저장할 수 있는 dict로 변환한다."""

    return {
        "template_version": REPORT_DOCUMENT_VERSION,
        "document": asdict(document),
    }
