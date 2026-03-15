"""리포트 생성 전용 서비스."""

from __future__ import annotations

import json
from pathlib import Path

from server.app.domain.models.report import Report
from server.app.domain.shared.enums import EventState, EventType
from server.app.repositories.contracts.meeting_event_repository import MeetingEventRepository
from server.app.repositories.contracts.report_repository import ReportRepository
from server.app.services.reports.audio.audio_postprocessing_service import (
    AudioPostprocessingService,
    SpeakerTranscriptSegment,
)
from server.app.services.reports.composition.markdown_report_builder import MarkdownReportBuilder
from server.app.services.reports.composition.simple_pdf_writer import write_text_pdf
from server.app.services.reports.composition.speaker_event_projection_service import (
    SpeakerAttributedEvent,
    SpeakerEventProjectionService,
)
from server.app.services.reports.refinement.report_refiner import (
    ReportRefinementEvent,
    ReportRefinementInput,
    ReportRefiner,
)
from server.app.services.reports.report_models import (
    BuiltMarkdownReport,
    BuiltPdfReport,
    PreparedReportContent,
    ReportInsightResolution,
    SavedReportArtifacts,
)


class ReportGenerationService:
    """리포트 생성과 artifact 저장만 담당한다."""

    def __init__(
        self,
        *,
        event_repository: MeetingEventRepository,
        report_repository: ReportRepository,
        markdown_report_builder: MarkdownReportBuilder,
        audio_postprocessing_service: AudioPostprocessingService | None = None,
        speaker_event_projection_service: SpeakerEventProjectionService | None = None,
        report_refiner: ReportRefiner | None = None,
    ) -> None:
        self._event_repository = event_repository
        self._report_repository = report_repository
        self._markdown_report_builder = markdown_report_builder
        self._audio_postprocessing_service = audio_postprocessing_service
        self._speaker_event_projection_service = speaker_event_projection_service
        self._report_refiner = report_refiner

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
        """같은 세션에서 새 버전 markdown/pdf 리포트를 생성한다."""

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

    @staticmethod
    def _build_output_path(
        *,
        output_dir: Path,
        session_id: str,
        report_type: str,
        version: int,
    ) -> Path:
        suffix = "md" if report_type == "markdown" else "pdf"
        session_dir = output_dir / session_id
        return session_dir / f"{report_type}.v{version}.{suffix}"

    def _prepare_report_content(
        self,
        *,
        session_id: str,
        audio_path: Path | None,
    ) -> PreparedReportContent:
        raw_markdown, speaker_transcript, speaker_events, report_insights = self._compose_raw_markdown(
            session_id=session_id,
            audio_path=audio_path,
        )
        markdown_content = self._refine_markdown(
            session_id=session_id,
            raw_markdown=raw_markdown,
            events=report_insights.events,
            speaker_transcript=speaker_transcript,
            speaker_events=speaker_events,
        )
        transcript_markdown = None
        analysis_snapshot = None
        if speaker_transcript:
            transcript_markdown = self._build_transcript_markdown(
                session_id=session_id,
                speaker_transcript=speaker_transcript,
            )
            analysis_snapshot = self._build_analysis_snapshot(
                session_id=session_id,
                insight_source=report_insights.insight_source,
                events=report_insights.events,
                speaker_transcript=speaker_transcript,
                speaker_events=speaker_events,
                refined_markdown=markdown_content,
            )
        return PreparedReportContent(
            markdown_content=markdown_content,
            speaker_transcript=speaker_transcript,
            speaker_events=speaker_events,
            insight_source=report_insights.insight_source,
            transcript_markdown=transcript_markdown,
            analysis_snapshot=analysis_snapshot,
        )

    def _save_markdown_report(
        self,
        *,
        session_id: str,
        output_dir: Path,
        prepared: PreparedReportContent,
        generated_by_user_id: str | None,
    ) -> BuiltMarkdownReport:
        version = self._report_repository.get_next_version(session_id, "markdown")
        output_path = self._build_output_path(
            output_dir=output_dir,
            session_id=session_id,
            report_type="markdown",
            version=version,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(prepared.markdown_content, encoding="utf-8")
        artifacts = self._write_pipeline_artifacts(
            output_path=output_path,
            prepared=prepared,
        )
        saved_report = self._report_repository.save(
            Report.create(
                session_id=session_id,
                report_type="markdown",
                version=version,
                file_path=str(output_path),
                insight_source=prepared.insight_source,
                generated_by_user_id=generated_by_user_id,
            )
        )
        return BuiltMarkdownReport(
            report=saved_report,
            content=prepared.markdown_content,
            speaker_transcript=prepared.speaker_transcript,
            speaker_events=prepared.speaker_events,
            transcript_path=artifacts.transcript_path,
            analysis_path=artifacts.analysis_path,
        )

    def _save_pdf_report(
        self,
        *,
        session_id: str,
        output_dir: Path,
        prepared: PreparedReportContent,
        generated_by_user_id: str | None,
    ) -> BuiltPdfReport:
        version = self._report_repository.get_next_version(session_id, "pdf")
        output_path = self._build_output_path(
            output_dir=output_dir,
            session_id=session_id,
            report_type="pdf",
            version=version,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        write_text_pdf(
            output_path=output_path,
            title="회의 리포트",
            lines=prepared.markdown_content.splitlines(),
        )
        artifacts = self._write_pipeline_artifacts(
            output_path=output_path,
            prepared=prepared,
        )
        saved_report = self._report_repository.save(
            Report.create(
                session_id=session_id,
                report_type="pdf",
                version=version,
                file_path=str(output_path),
                insight_source=prepared.insight_source,
                generated_by_user_id=generated_by_user_id,
            )
        )
        return BuiltPdfReport(
            report=saved_report,
            source_markdown=prepared.markdown_content,
            transcript_path=artifacts.transcript_path,
            analysis_path=artifacts.analysis_path,
        )

    def _compose_raw_markdown(
        self,
        *,
        session_id: str,
        audio_path: Path | None,
    ) -> tuple[str, list[SpeakerTranscriptSegment], list[SpeakerAttributedEvent], ReportInsightResolution]:
        live_events = self._event_repository.list_by_session(
            session_id,
            insight_scope="live",
        )
        speaker_transcript: list[SpeakerTranscriptSegment] = []
        speaker_events: list[SpeakerAttributedEvent] = []

        if audio_path is not None and self._audio_postprocessing_service is not None:
            speaker_transcript = self._audio_postprocessing_service.build_speaker_transcript(audio_path)
            if self._speaker_event_projection_service is not None:
                speaker_events = self._speaker_event_projection_service.project(
                    session_id=session_id,
                    speaker_transcript=speaker_transcript,
                )

        report_insights = self._resolve_report_insights(
            live_events=live_events,
            speaker_events=speaker_events,
        )
        raw_markdown = self._markdown_report_builder.build(
            session_id=session_id,
            events=report_insights.events,
            speaker_transcript=speaker_transcript,
            speaker_events=speaker_events,
        )
        return raw_markdown, speaker_transcript, speaker_events, report_insights

    def _refine_markdown(
        self,
        *,
        session_id: str,
        raw_markdown: str,
        events: list,
        speaker_transcript: list[SpeakerTranscriptSegment],
        speaker_events: list[SpeakerAttributedEvent],
    ) -> str:
        if self._report_refiner is None:
            return raw_markdown

        return self._report_refiner.refine(
            ReportRefinementInput(
                session_id=session_id,
                raw_markdown=raw_markdown,
                events=[
                    ReportRefinementEvent(
                        event_type=event.event_type.value,
                        title=event.title,
                        state=event.state.value,
                        evidence_text=event.evidence_text,
                        speaker_label=event.speaker_label,
                        input_source=event.input_source,
                    )
                    for event in events
                ],
                event_lines=[f"[{event.event_type.value}] {event.title}" for event in events],
                speaker_transcript_lines=[
                    (
                        f"{self._format_timeline_range(segment.start_ms, segment.end_ms)} "
                        f"{segment.text}"
                    )
                    for segment in speaker_transcript
                ],
                speaker_event_lines=[
                    f"[{item.event.event_type.value}] {item.speaker_label}: {item.event.title}"
                    for item in speaker_events
                ],
            )
        )

    @staticmethod
    def _build_transcript_markdown(
        *,
        session_id: str,
        speaker_transcript: list[SpeakerTranscriptSegment],
    ) -> str:
        lines = [
            "# 고정밀 전사 결과",
            "",
            f"- 세션 ID: {session_id}",
            f"- 전사 구간 수: {len(speaker_transcript)}",
            "",
        ]
        for segment in speaker_transcript:
            lines.append(
                f"- [{segment.speaker_label}] "
                f"{segment.start_ms}ms-{segment.end_ms}ms "
                f"(confidence={segment.confidence:.3f})"
            )
            lines.append(f"  {segment.text}")
        return "\n".join(lines)

    @staticmethod
    def _format_timeline_range(start_ms: int, end_ms: int) -> str:
        return (
            f"{ReportGenerationService._format_mmss(start_ms)}-"
            f"{ReportGenerationService._format_mmss(end_ms)}"
        )

    @staticmethod
    def _format_mmss(value_ms: int) -> str:
        total_seconds = max(int(value_ms // 1000), 0)
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"

    @staticmethod
    def _build_analysis_snapshot(
        *,
        session_id: str,
        insight_source: str,
        events: list,
        speaker_transcript: list[SpeakerTranscriptSegment],
        speaker_events: list[SpeakerAttributedEvent],
        refined_markdown: str,
    ) -> dict[str, object]:
        return {
            "session_id": session_id,
            "insight_source": insight_source,
            "event_count": len(events),
            "speaker_transcript_count": len(speaker_transcript),
            "speaker_event_count": len(speaker_events),
            "events": [
                {
                    "event_type": event.event_type.value,
                    "title": event.title,
                    "state": event.state.value,
                    "speaker_label": event.speaker_label,
                    "input_source": event.input_source,
                    "evidence_text": event.evidence_text,
                }
                for event in events
            ],
            "speaker_transcript": [
                {
                    "speaker_label": segment.speaker_label,
                    "start_ms": segment.start_ms,
                    "end_ms": segment.end_ms,
                    "text": segment.text,
                    "confidence": segment.confidence,
                }
                for segment in speaker_transcript
            ],
            "speaker_events": [
                {
                    "speaker_label": item.speaker_label,
                    "event_type": item.event.event_type.value,
                    "title": item.event.title,
                    "state": item.event.state.value,
                }
                for item in speaker_events
            ],
            "refined_markdown": refined_markdown,
        }

    def _write_pipeline_artifacts(
        self,
        *,
        output_path: Path,
        prepared: PreparedReportContent,
    ) -> SavedReportArtifacts:
        transcript_path: str | None = None
        analysis_path: str | None = None
        artifacts_dir = output_path.parent / "artifacts"

        if prepared.transcript_markdown:
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            transcript_file_path = artifacts_dir / f"{output_path.stem}.transcript.md"
            transcript_file_path.write_text(prepared.transcript_markdown, encoding="utf-8")
            transcript_path = str(transcript_file_path)

        if prepared.analysis_snapshot is not None:
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            analysis_file_path = artifacts_dir / f"{output_path.stem}.analysis.json"
            analysis_file_path.write_text(
                json.dumps(prepared.analysis_snapshot, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            analysis_path = str(analysis_file_path)

        return SavedReportArtifacts(
            transcript_path=transcript_path,
            analysis_path=analysis_path,
        )

    @staticmethod
    def _resolve_report_insights(
        *,
        live_events: list,
        speaker_events: list[SpeakerAttributedEvent],
    ) -> ReportInsightResolution:
        def _is_reportable(event) -> bool:
            if event.event_type == EventType.DECISION:
                return event.state in {EventState.CONFIRMED, EventState.UPDATED, EventState.CLOSED}
            if event.event_type == EventType.ACTION_ITEM:
                return event.state in {EventState.OPEN, EventState.CLOSED}
            if event.event_type == EventType.QUESTION:
                return event.state in {EventState.OPEN, EventState.ANSWERED, EventState.CLOSED}
            if event.event_type == EventType.RISK:
                return event.state in {EventState.OPEN, EventState.RESOLVED, EventState.CLOSED}
            return event.state != EventState.CLOSED

        if speaker_events:
            return ReportInsightResolution(
                events=[item.event for item in speaker_events if _is_reportable(item.event)],
                insight_source="high_precision_audio",
            )
        return ReportInsightResolution(
            events=[event for event in live_events if _is_reportable(event)],
            insight_source="live_fallback",
        )
