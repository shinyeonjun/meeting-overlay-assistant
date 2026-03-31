"""history 응답 스키마"""

from pydantic import BaseModel


class HistoryTimelineSessionItemResponse(BaseModel):
    """history 타임라인의 최근 회의 항목."""

    id: str
    title: str
    status: str
    primary_input_source: str
    started_at: str
    account_id: str | None = None
    contact_id: str | None = None
    context_thread_id: str | None = None


class HistoryTimelineReportItemResponse(BaseModel):
    """history 타임라인의 최근 리포트 항목."""

    id: str
    session_id: str
    report_type: str
    version: int
    generated_at: str
    file_artifact_id: str | None = None
    file_path: str
    insight_source: str


class HistoryCarryOverItemResponse(BaseModel):
    """이전 미팅에서 다음 미팅으로 이어볼 이벤트 항목."""

    event_id: str
    session_id: str
    session_title: str
    event_type: str
    title: str
    state: str
    updated_at_ms: int


class HistoryCarryOverResponse(BaseModel):
    """history carry-over 브리프."""

    decisions: list[HistoryCarryOverItemResponse]
    action_items: list[HistoryCarryOverItemResponse]
    risks: list[HistoryCarryOverItemResponse]
    questions: list[HistoryCarryOverItemResponse]


class HistoryRetrievalBriefItemResponse(BaseModel):
    """관련 과거 문서 조각."""

    chunk_id: str
    document_id: str
    source_type: str
    source_id: str
    document_title: str
    chunk_text: str
    chunk_heading: str | None = None
    distance: float
    session_id: str | None = None
    report_id: str | None = None
    account_id: str | None = None
    contact_id: str | None = None
    context_thread_id: str | None = None


class HistoryRetrievalBriefResponse(BaseModel):
    """history retrieval 브리프."""

    query: str | None = None
    result_count: int
    items: list[HistoryRetrievalBriefItemResponse]


class HistoryTimelineResponse(BaseModel):
    """맥락 기반 history 타임라인 응답."""

    account_id: str | None = None
    contact_id: str | None = None
    context_thread_id: str | None = None
    session_count: int
    report_count: int
    sessions: list[HistoryTimelineSessionItemResponse]
    reports: list[HistoryTimelineReportItemResponse]
    carry_over: HistoryCarryOverResponse
    retrieval_brief: HistoryRetrievalBriefResponse
