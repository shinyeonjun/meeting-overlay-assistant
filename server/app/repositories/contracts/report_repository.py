"""회의록 저장소 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod

from server.app.domain.models.report import Report
from server.app.services.reports.report_models import SessionReportSummary


class ReportRepository(ABC):
    """회의록 저장소 인터페이스."""

    @abstractmethod
    def save(self, report: Report) -> Report:
        raise NotImplementedError

    @abstractmethod
    def list_by_session(self, session_id: str) -> list[Report]:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, report_id: str) -> Report | None:
        raise NotImplementedError

    @abstractmethod
    def get_next_version(self, session_id: str, report_type: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def list_recent(
        self,
        *,
        generated_by_user_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
        limit: int | None = 50,
    ) -> list[Report]:
        raise NotImplementedError

    @abstractmethod
    def count_recent(
        self,
        *,
        generated_by_user_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    def get_session_summaries(self, session_ids: list[str]) -> dict[str, SessionReportSummary]:
        raise NotImplementedError
