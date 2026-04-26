"""회의록 저장 helper."""

from __future__ import annotations

from pathlib import Path

from server.app.domain.models.report import Report
from server.app.services.reports.composition.simple_pdf_writer import write_text_pdf
from server.app.services.reports.generation.helpers.artifact_outputs import (
    build_output_destination,
    write_pipeline_artifacts,
)
from server.app.services.reports.report_models import (
    BuiltMarkdownReport,
    BuiltPdfReport,
    PreparedReportContent,
)


def save_markdown_report(
    *,
    session_id: str,
    output_dir: Path,
    prepared: PreparedReportContent,
    generated_by_user_id: str | None,
    report_repository,
    artifact_store,
) -> BuiltMarkdownReport:
    """Markdown 회의록을 파일과 저장소에 함께 저장한다."""

    version = report_repository.get_next_version(session_id, "markdown")
    file_artifact_id, output_path = build_output_destination(
        artifact_store=artifact_store,
        output_dir=output_dir,
        session_id=session_id,
        report_type="markdown",
        version=version,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(prepared.markdown_content, encoding="utf-8")
    artifacts = write_pipeline_artifacts(
        output_path=output_path,
        prepared=prepared,
    )
    saved_report = report_repository.save(
        Report.create(
            session_id=session_id,
            report_type="markdown",
            version=version,
            file_artifact_id=file_artifact_id,
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
        html_path=artifacts.html_path,
        document_path=artifacts.document_path,
    )


def save_pdf_report(
    *,
    session_id: str,
    output_dir: Path,
    prepared: PreparedReportContent,
    generated_by_user_id: str | None,
    report_repository,
    artifact_store,
) -> BuiltPdfReport:
    """PDF 회의록을 파일과 저장소에 함께 저장한다."""

    version = report_repository.get_next_version(session_id, "pdf")
    file_artifact_id, output_path = build_output_destination(
        artifact_store=artifact_store,
        output_dir=output_dir,
        session_id=session_id,
        report_type="pdf",
        version=version,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_text_pdf(
        output_path=output_path,
        title=prepared.report_document.title,
        lines=prepared.markdown_content.splitlines(),
    )
    artifacts = write_pipeline_artifacts(
        output_path=output_path,
        prepared=prepared,
    )
    saved_report = report_repository.save(
        Report.create(
            session_id=session_id,
            report_type="pdf",
            version=version,
            file_artifact_id=file_artifact_id,
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
        html_path=artifacts.html_path,
        document_path=artifacts.document_path,
    )
