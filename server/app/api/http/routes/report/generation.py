"""리포트 생성 라우트."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from server.app.api.http.access_control import get_accessible_session_or_raise
from server.app.api.http.schemas.report import (
    MarkdownReportResponse,
    PdfReportResponse,
    RegenerateReportsResponse,
    RegeneratedReportItemResponse,
    SpeakerEventItemResponse,
    SpeakerTranscriptItemResponse,
)
from server.app.api.http.security import require_authenticated_session
from server.app.core.config import ROOT_DIR
from server.app.domain.models.auth_session import AuthenticatedSession

router = APIRouter()


def _reports_facade():
    from server.app.api.http import routes as api_routes

    return api_routes.reports


@router.post("/{session_id}/markdown", response_model=MarkdownReportResponse)
def create_markdown_report(
    session_id: str,
    audio_path: str | None = None,
    audio_artifact_id: str | None = None,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> MarkdownReportResponse:
    """세션 리포트를 Markdown으로 생성한다."""

    get_accessible_session_or_raise(session_id, auth_context)
    report_service = _reports_facade().get_report_service()
    output_dir = ROOT_DIR / "server" / "data" / "reports"
    try:
        result = report_service.build_markdown_report(
            session_id=session_id,
            output_dir=Path(output_dir),
            audio_path=_reports_facade()._resolve_audio_path(
                session_id,
                audio_path,
                audio_artifact_id,
            ),
            generated_by_user_id=auth_context.user.id if auth_context is not None else None,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return MarkdownReportResponse(
        id=result.report.id,
        session_id=result.report.session_id,
        report_type=result.report.report_type,
        version=result.report.version,
        file_artifact_id=result.report.file_artifact_id,
        file_path=result.report.file_path,
        insight_source=result.report.insight_source,
        generated_by_user_id=result.report.generated_by_user_id,
        content=result.content,
        transcript_path=result.transcript_path,
        analysis_path=result.analysis_path,
        html_path=result.html_path,
        speaker_transcript=[
            SpeakerTranscriptItemResponse(
                speaker_label=item.speaker_label,
                start_ms=item.start_ms,
                end_ms=item.end_ms,
                text=item.text,
                confidence=item.confidence,
            )
            for item in result.speaker_transcript
        ],
        speaker_events=[
            SpeakerEventItemResponse(
                speaker_label=item.speaker_label,
                event_type=item.event.event_type.value,
                title=item.event.title,
                state=item.event.state.value,
            )
            for item in result.speaker_events
        ],
    )


@router.post("/{session_id}/pdf", response_model=PdfReportResponse)
def create_pdf_report(
    session_id: str,
    audio_path: str | None = None,
    audio_artifact_id: str | None = None,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> PdfReportResponse:
    """세션 리포트를 PDF로 생성한다."""

    get_accessible_session_or_raise(session_id, auth_context)
    report_service = _reports_facade().get_report_service()
    output_dir = ROOT_DIR / "server" / "data" / "reports"
    try:
        result = report_service.build_pdf_report(
            session_id=session_id,
            output_dir=Path(output_dir),
            audio_path=_reports_facade()._resolve_audio_path(
                session_id,
                audio_path,
                audio_artifact_id,
            ),
            generated_by_user_id=auth_context.user.id if auth_context is not None else None,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return PdfReportResponse(
        id=result.report.id,
        session_id=result.report.session_id,
        report_type=result.report.report_type,
        version=result.report.version,
        file_artifact_id=result.report.file_artifact_id,
        file_path=result.report.file_path,
        insight_source=result.report.insight_source,
        generated_by_user_id=result.report.generated_by_user_id,
        source_markdown=result.source_markdown,
        transcript_path=result.transcript_path,
        analysis_path=result.analysis_path,
        html_path=result.html_path,
    )


@router.post("/{session_id}/regenerate", response_model=RegenerateReportsResponse)
def regenerate_reports(
    session_id: str,
    audio_path: str | None = None,
    audio_artifact_id: str | None = None,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> RegenerateReportsResponse:
    """같은 세션에서 새 버전 markdown/pdf 리포트를 만든다."""

    get_accessible_session_or_raise(session_id, auth_context)
    report_service = _reports_facade().get_report_service()
    output_dir = ROOT_DIR / "server" / "data" / "reports"
    try:
        markdown_report, pdf_report = report_service.regenerate_reports(
            session_id=session_id,
            output_dir=Path(output_dir),
            audio_path=_reports_facade()._resolve_audio_path(
                session_id,
                audio_path,
                audio_artifact_id,
            ),
            generated_by_user_id=auth_context.user.id if auth_context is not None else None,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return RegenerateReportsResponse(
        session_id=session_id,
        items=[
            RegeneratedReportItemResponse(
                id=markdown_report.report.id,
                report_type=markdown_report.report.report_type,
                version=markdown_report.report.version,
                file_artifact_id=markdown_report.report.file_artifact_id,
                file_path=markdown_report.report.file_path,
                insight_source=markdown_report.report.insight_source,
                generated_by_user_id=markdown_report.report.generated_by_user_id,
            ),
            RegeneratedReportItemResponse(
                id=pdf_report.report.id,
                report_type=pdf_report.report.report_type,
                version=pdf_report.report.version,
                file_artifact_id=pdf_report.report.file_artifact_id,
                file_path=pdf_report.report.file_path,
                insight_source=pdf_report.report.insight_source,
                generated_by_user_id=pdf_report.report.generated_by_user_id,
            ),
        ],
    )
