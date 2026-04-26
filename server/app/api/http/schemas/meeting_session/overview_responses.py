"""세션 overview 응답 스키마."""

from pydantic import BaseModel

from server.app.api.http.schemas.meeting_session.responses import SessionResponse


class OverviewEventItemResponse(BaseModel):
    """overview 이벤트 요약 항목."""

    id: str
    title: str
    state: str
    speaker_label: str | None = None


class OverviewMetricsResponse(BaseModel):
    """overview 운영 지표."""

    recent_average_latency_ms: float | None = None
    recent_utterance_count_by_source: dict[str, int]
    insight_metrics: dict[str, int] | None = None


class WorkspaceSummaryActionItemResponse(BaseModel):
    """사용자용 workspace summary 후속 작업 항목."""

    title: str
    owner: str | None = None
    due_date: str | None = None


class WorkspaceSummaryEvidenceResponse(BaseModel):
    """사용자용 workspace summary 근거 구간."""

    label: str
    start_ms: int
    end_ms: int


class WorkspaceSummaryTopicResponse(BaseModel):
    """사용자용 workspace summary 주제 흐름 항목."""

    title: str
    summary: str
    start_ms: int
    end_ms: int


class WorkspaceSummaryResponse(BaseModel):
    """사용자용 workspace summary 응답."""

    headline: str
    summary: list[str]
    topics: list[WorkspaceSummaryTopicResponse]
    decisions: list[str]
    next_actions: list[WorkspaceSummaryActionItemResponse]
    open_questions: list[str]
    changed_since_last_meeting: list[str]
    evidence: list[WorkspaceSummaryEvidenceResponse]
    model: str


class SessionOverviewResponse(BaseModel):
    """세션 overview 응답."""

    session: SessionResponse
    current_topic: str | None
    questions: list[OverviewEventItemResponse]
    decisions: list[OverviewEventItemResponse]
    action_items: list[OverviewEventItemResponse]
    risks: list[OverviewEventItemResponse]
    workspace_summary: WorkspaceSummaryResponse | None = None
    metrics: OverviewMetricsResponse
