"""리포트 저장소 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.app.domain.models.report import Report


class ReportRepository(ABC):
    """리포트 저장소 인터페이스."""

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
