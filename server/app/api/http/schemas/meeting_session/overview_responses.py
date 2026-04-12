"""HTTP 계층에서 공통 관련 overview responses 구성을 담당한다."""
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


class SessionOverviewResponse(BaseModel):
    """세션 overview 응답."""

    session: SessionResponse
    current_topic: str | None
    questions: list[OverviewEventItemResponse]
    decisions: list[OverviewEventItemResponse]
    action_items: list[OverviewEventItemResponse]
    risks: list[OverviewEventItemResponse]
    metrics: OverviewMetricsResponse
