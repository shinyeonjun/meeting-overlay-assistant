"""회의록 공유 저장소 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod

from server.app.domain.models.report_share import (
    ReceivedReportShareView,
    ReportShare,
    ReportShareView,
)


class ReportShareRepository(ABC):
    """회의록 공유 저장소 인터페이스."""

    @abstractmethod
    def save(self, share: ReportShare) -> ReportShareView:
        raise NotImplementedError

    @abstractmethod
    def get_by_report_and_recipient(
        self,
        *,
        report_id: str,
        shared_with_user_id: str,
    ) -> ReportShare | None:
        raise NotImplementedError

    @abstractmethod
    def list_by_report(self, report_id: str) -> list[ReportShareView]:
        raise NotImplementedError

    @abstractmethod
    def list_received_by_user(
        self,
        *,
        shared_with_user_id: str,
        limit: int = 50,
    ) -> list[ReceivedReportShareView]:
        raise NotImplementedError
