"""세션 종료 orchestration 서비스"""

from __future__ import annotations

from backend.app.domain.models.session import MeetingSession
from backend.app.services.reports.core.report_service import ReportService
from backend.app.services.sessions.session_service import SessionService


class SessionFinalizationService:
    """세션 종료 시점의 후처리를 담당한다."""

    def __init__(
        self,
        session_service: SessionService,
        report_service: ReportService,
    ) -> None:
        self._session_service = session_service
        self._report_service = report_service

    def finalize_session(self, session_id: str) -> MeetingSession:
        """세션을 종료한다.

        리포트 생성은 별도 수동 흐름에서 처리한다.
        """

        return self._session_service.end_session(session_id)
