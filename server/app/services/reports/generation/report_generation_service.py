"""리포트 생성 전용 서비스."""

from __future__ import annotations

from pathlib import Path

from server.app.infrastructure.artifacts import LocalArtifactStore
from server.app.repositories.contracts.meeting_event_repository import (
    MeetingEventRepository,
)
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
from server.app.services.reports.generation.helpers.content_preparation import (
    prepare_report_content,
)
from server.app.services.reports.generation.helpers.generation_readiness import (
    resolve_report_generation_readiness,
)
from server.app.services.reports.generation.helpers.report_persistence import (
    save_markdown_report,
    save_pdf_report,
)
from server.app.services.reports.refinement.report_refiner import ReportRefiner
from server.app.services.reports.report_models import (
    BuiltMarkdownReport,
    BuiltPdfReport,
    PreparedReportContent,
)


class ReportGenerationService:
    """리포트 생성과 artifact 저장만 담당한다."""

    def __init__(
        self,
        *,
        event_repository: MeetingEventRepository,
        report_repository: ReportRepository,
        markdown_report_builder: MarkdownReportBuilder,
        utterance_repository=None,
        audio_postprocessing_service: AudioPostprocessingService | None = None,
        speaker_event_projection_service: SpeakerEventProjectionService | None = None,
        report_refiner: ReportRefiner | None = None,
        artifact_store: LocalArtifactStore | None = None,
    ) -> None:
        self._event_repository = event_repository
        self._report_repository = report_repository
        self._markdown_report_builder = markdown_report_builder
        self._utterance_repository = utterance_repository
        self._audio_postprocessing_service = audio_postprocessing_service
        self._speaker_event_projection_service = speaker_event_projection_service
        self._report_refiner = report_refiner
        self._artifact_store = artifact_store

    def build_markdown_report(
        self,
        session_id: str,
        output_dir: Path,
        audio_path: Path | None = None,
        *,
        generated_by_user_id: str | None = None,
    ) -> BuiltMarkdownReport:
        """세션 리포트를 Markdown으로 생성한다."""

        prepared = self._prepare_report_content(
            session_id=session_id,
            audio_path=audio_path,
        )
        return self._save_markdown_report(
            session_id=session_id,
            output_dir=output_dir,
            prepared=prepared,
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
        """세션 리포트를 PDF로 생성한다."""

        prepared = self._prepare_report_content(
            session_id=session_id,
            audio_path=audio_path,
        )
        return self._save_pdf_report(
            session_id=session_id,
            output_dir=output_dir,
            prepared=prepared,
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
        """같은 세션에서 새 버전 markdown/pdf 리포트를 함께 생성한다."""

        prepared = self._prepare_report_content(
            session_id=session_id,
            audio_path=audio_path,
        )
        markdown_report = self._save_markdown_report(
            session_id=session_id,
            output_dir=output_dir,
            prepared=prepared,
            generated_by_user_id=generated_by_user_id,
        )
        pdf_report = self._save_pdf_report(
            session_id=session_id,
            output_dir=output_dir,
            prepared=prepared,
            generated_by_user_id=generated_by_user_id,
        )
        return markdown_report, pdf_report

    def _prepare_report_content(
        self,
        *,
        session_id: str,
        audio_path: Path | None,
    ) -> PreparedReportContent:
        readiness = resolve_report_generation_readiness(
            session_id=session_id,
            audio_path=audio_path,
            event_repository=self._event_repository,
            utterance_repository=self._utterance_repository,
        )
        return prepare_report_content(
            session_id=session_id,
            audio_path=readiness.audio_path,
            live_events=readiness.live_events,
            reference_transcript_lines=readiness.transcript_lines,
            canonical_speaker_transcript=readiness.speaker_transcript,
            event_repository=self._event_repository,
            markdown_report_builder=self._markdown_report_builder,
            audio_postprocessing_service=self._audio_postprocessing_service,
            speaker_event_projection_service=self._speaker_event_projection_service,
            report_refiner=self._report_refiner,
        )

    def _save_markdown_report(
        self,
        *,
        session_id: str,
        output_dir: Path,
        prepared: PreparedReportContent,
        generated_by_user_id: str | None,
    ) -> BuiltMarkdownReport:
        return save_markdown_report(
            session_id=session_id,
            output_dir=output_dir,
            prepared=prepared,
            generated_by_user_id=generated_by_user_id,
            report_repository=self._report_repository,
            artifact_store=self._artifact_store,
        )

    def _save_pdf_report(
        self,
        *,
        session_id: str,
        output_dir: Path,
        prepared: PreparedReportContent,
        generated_by_user_id: str | None,
    ) -> BuiltPdfReport:
        return save_pdf_report(
            session_id=session_id,
            output_dir=output_dir,
            prepared=prepared,
            generated_by_user_id=generated_by_user_id,
            report_repository=self._report_repository,
            artifact_store=self._artifact_store,
        )
