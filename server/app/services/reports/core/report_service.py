"""리포트 영역의 report service 서비스를 제공한다."""
from __future__ import annotations

from pathlib import Path

from server.app.infrastructure.artifacts import LocalArtifactStore
from server.app.repositories.contracts.meeting_event_repository import MeetingEventRepository
from server.app.repositories.contracts.report_repository import ReportRepository
from server.app.services.reports.audio.audio_postprocessing_service import (
    AudioPostprocessingService,
)
from server.app.services.reports.composition.markdown_report_builder import (
    MarkdownReportBuilder,
)
from server.app.services.reports.composition.speaker_event_projection_service import (
    SpeakerEventProjectionService,
)
from server.app.services.reports.generation.report_generation_service import (
    ReportGenerationService,
)
from server.app.services.reports.query.report_query_service import ReportQueryService
from server.app.services.reports.refinement.report_refiner import ReportRefiner
from server.app.services.reports.report_models import (
    BuiltMarkdownReport,
    BuiltPdfReport,
    FinalReportStatus,
    SessionReportSummary,
)


class ReportService:
    """리포트 생성과 조회를 묶는 호환 facade."""

    def __init__(
        self,
        event_repository: MeetingEventRepository,
        report_repository: ReportRepository,
        markdown_report_builder: MarkdownReportBuilder,
        utterance_repository=None,
        audio_postprocessing_service: AudioPostprocessingService | None = None,
        speaker_event_projection_service: SpeakerEventProjectionService | None = None,
        report_refiner: ReportRefiner | None = None,
        artifact_store: LocalArtifactStore | None = None,
        transcript_correction_store=None,
    ) -> None:
        self._generation_service = ReportGenerationService(
            event_repository=event_repository,
            report_repository=report_repository,
            markdown_report_builder=markdown_report_builder,
            utterance_repository=utterance_repository,
            audio_postprocessing_service=audio_postprocessing_service,
            speaker_event_projection_service=speaker_event_projection_service,
            report_refiner=report_refiner,
            artifact_store=artifact_store,
            transcript_correction_store=transcript_correction_store,
        )
        self._query_service = ReportQueryService(
            report_repository,
            artifact_store=artifact_store,
        )

    @property
    def generation(self) -> ReportGenerationService:
        """리포트 생성 서비스에 접근한다."""

        return self._generation_service

    @property
    def query(self) -> ReportQueryService:
        """리포트 조회 서비스에 접근한다."""

        return self._query_service

    def build_markdown_report(
        self,
        session_id: str,
        output_dir: Path,
        audio_path: Path | None = None,
        *,
        generated_by_user_id: str | None = None,
    ) -> BuiltMarkdownReport:
        return self._generation_service.build_markdown_report(
            session_id=session_id,
            output_dir=output_dir,
            audio_path=audio_path,
            generated_by_user_id=generated_by_user_id,
        )

    def build_pdf_report(
        self,
        session_id: str,
        output_dir: Path,
        audio_path: Path | None = None,
        *,
        generated_by_user_id: str | None = None,
    ) -> BuiltPdfReport:
        return self._generation_service.build_pdf_report(
            session_id=session_id,
            output_dir=output_dir,
            audio_path=audio_path,
            generated_by_user_id=generated_by_user_id,
        )

    def regenerate_reports(
        self,
        session_id: str,
        output_dir: Path,
        audio_path: Path | None = None,
        *,
        generated_by_user_id: str | None = None,
    ) -> tuple[BuiltMarkdownReport, BuiltPdfReport]:
        return self._generation_service.regenerate_reports(
            session_id=session_id,
            output_dir=output_dir,
            audio_path=audio_path,
            generated_by_user_id=generated_by_user_id,
        )

    def list_reports(self, session_id: str):
        return self._query_service.list_reports(session_id)

    def get_latest_report(self, session_id: str):
        return self._query_service.get_latest_report(session_id)

    def get_report_by_id(self, report_id: str):
        return self._query_service.get_report_by_id(report_id)

    def list_recent_reports(
        self,
        *,
        generated_by_user_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
        limit: int = 50,
    ):
        return self._query_service.list_recent_reports(
            generated_by_user_id=generated_by_user_id,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
            limit=limit,
        )

    def count_recent_reports(
        self,
        *,
        generated_by_user_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
    ) -> int:
        return self._query_service.count_recent_reports(
            generated_by_user_id=generated_by_user_id,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
        )

    def get_session_report_summaries(
        self,
        session_ids: list[str],
    ) -> dict[str, SessionReportSummary]:
        return self._query_service.get_session_report_summaries(session_ids)

    def get_final_status(self, *, session_id: str, session_ended: bool) -> FinalReportStatus:
        return self._query_service.get_final_status(
            session_id=session_id,
            session_ended=session_ended,
        )

    def read_report_content(self, report) -> str | None:
        return self._query_service.read_report_content(report)

    def resolve_report_path(self, report):
        return self._query_service.resolve_report_path(report)

    def report_exists(self, report) -> bool:
        return self._query_service.report_exists(report)
