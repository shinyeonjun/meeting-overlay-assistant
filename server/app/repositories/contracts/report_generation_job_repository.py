"""리포트 생성 job 저장소 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod

from server.app.domain.models.report_generation_job import ReportGenerationJob


class ReportGenerationJobRepository(ABC):
    """리포트 생성 job 저장소 인터페이스."""

    @abstractmethod
    def save(self, job: ReportGenerationJob) -> ReportGenerationJob:
        raise NotImplementedError

    @abstractmethod
    def update(self, job: ReportGenerationJob) -> ReportGenerationJob:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, job_id: str) -> ReportGenerationJob | None:
        raise NotImplementedError

    @abstractmethod
    def get_latest_by_session(self, session_id: str) -> ReportGenerationJob | None:
        raise NotImplementedError
