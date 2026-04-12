"""HTTP 계층에서 공통 관련 workspace 구성을 담당한다."""
from pydantic import BaseModel

from server.app.api.http.schemas.history.responses import (
    HistoryCarryOverResponse,
    HistoryRetrievalBriefResponse,
    HistoryTimelineReportItemResponse,
    HistoryTimelineSessionItemResponse,
)
from server.app.api.http.schemas.report import FinalReportStatusResponse


class WorkspaceOverviewSummaryResponse(BaseModel):
    """workspace 첫 화면에 필요한 요약 지표."""

    active_session_count: int
    loaded_session_count: int
    report_count: int


class WorkspaceOverviewResponse(BaseModel):
    """web workspace overview 집계 응답."""

    workspace_id: str
    scope: str
    account_id: str | None = None
    contact_id: str | None = None
    context_thread_id: str | None = None
    summary: WorkspaceOverviewSummaryResponse
    sessions: list[HistoryTimelineSessionItemResponse]
    report_statuses: dict[str, FinalReportStatusResponse]
    reports: list[HistoryTimelineReportItemResponse]
    carry_over: HistoryCarryOverResponse
    retrieval_brief: HistoryRetrievalBriefResponse
