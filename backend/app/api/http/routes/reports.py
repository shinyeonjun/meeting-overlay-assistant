"""리포트 라우터."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.app.api.http.dependencies import get_report_service, get_session_service
from backend.app.api.http.schemas.report import (
    FinalReportStatusResponse,
    LatestReportResponse,
    MarkdownReportResponse,
    PdfReportResponse,
    RegenerateReportsResponse,
    RegeneratedReportItemResponse,
    ReportItemResponse,
    ReportListResponse,
    SpeakerEventItemResponse,
    SpeakerTranscriptItemResponse,
)
from backend.app.core.config import ROOT_DIR


router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.post("/{session_id}/markdown", response_model=MarkdownReportResponse)
def create_markdown_report(session_id: str, audio_path: str | None = None) -> MarkdownReportResponse:
    """세션 이벤트를 기준으로 Markdown 리포트를 생성한다."""

    report_service = get_report_service()
    output_dir = ROOT_DIR / "backend" / "data" / "reports"
    result = report_service.build_markdown_report(
        session_id=session_id,
        output_dir=Path(output_dir),
        audio_path=Path(audio_path) if audio_path else None,
    )
    return MarkdownReportResponse(
        id=result.report.id,
        session_id=result.report.session_id,
        report_type=result.report.report_type,
        version=result.report.version,
        file_path=result.report.file_path,
        insight_source=result.report.insight_source,
        content=result.content,
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


@router.get("/{session_id}", response_model=ReportListResponse)
def list_reports(session_id: str) -> ReportListResponse:
    """세션 리포트 목록을 조회한다."""

    report_service = get_report_service()
    reports = report_service.list_reports(session_id)
    return ReportListResponse(
        items=[
            ReportItemResponse(
                id=report.id,
                session_id=report.session_id,
                report_type=report.report_type,
                version=report.version,
                file_path=report.file_path,
                insight_source=report.insight_source,
                generated_at=report.generated_at,
            )
            for report in reports
        ]
    )


@router.get("/{session_id}/latest", response_model=LatestReportResponse)
def get_latest_report(session_id: str) -> LatestReportResponse:
    """세션의 최신 리포트를 조회한다."""

    report_service = get_report_service()
    latest_report = report_service.get_latest_report(session_id)
    if latest_report is None:
        raise HTTPException(status_code=404, detail="리포트가 아직 생성되지 않았습니다.")
    return LatestReportResponse(
        id=latest_report.id,
        session_id=latest_report.session_id,
        report_type=latest_report.report_type,
        version=latest_report.version,
        file_path=latest_report.file_path,
        insight_source=latest_report.insight_source,
        generated_at=latest_report.generated_at,
        content=report_service.read_report_content(latest_report),
    )


@router.post("/{session_id}/pdf", response_model=PdfReportResponse)
def create_pdf_report(session_id: str, audio_path: str | None = None) -> PdfReportResponse:
    """세션 이벤트를 기준으로 PDF 리포트를 생성한다."""

    report_service = get_report_service()
    output_dir = ROOT_DIR / "backend" / "data" / "reports"
    result = report_service.build_pdf_report(
        session_id=session_id,
        output_dir=Path(output_dir),
        audio_path=Path(audio_path) if audio_path else None,
    )
    return PdfReportResponse(
        id=result.report.id,
        session_id=result.report.session_id,
        report_type=result.report.report_type,
        version=result.report.version,
        file_path=result.report.file_path,
        insight_source=result.report.insight_source,
        source_markdown=result.source_markdown,
    )


@router.post("/{session_id}/regenerate", response_model=RegenerateReportsResponse)
def regenerate_reports(session_id: str, audio_path: str | None = None) -> RegenerateReportsResponse:
    """같은 세션에 대한 새 버전 markdown/pdf 리포트를 재생성한다."""

    report_service = get_report_service()
    output_dir = ROOT_DIR / "backend" / "data" / "reports"
    markdown_report, pdf_report = report_service.regenerate_reports(
        session_id=session_id,
        output_dir=Path(output_dir),
        audio_path=Path(audio_path) if audio_path else None,
    )
    return RegenerateReportsResponse(
        session_id=session_id,
        items=[
            RegeneratedReportItemResponse(
                id=markdown_report.report.id,
                report_type=markdown_report.report.report_type,
                version=markdown_report.report.version,
                file_path=markdown_report.report.file_path,
                insight_source=markdown_report.report.insight_source,
            ),
            RegeneratedReportItemResponse(
                id=pdf_report.report.id,
                report_type=pdf_report.report.report_type,
                version=pdf_report.report.version,
                file_path=pdf_report.report.file_path,
                insight_source=pdf_report.report.insight_source,
            ),
        ],
    )


@router.get("/{session_id}/final-status", response_model=FinalReportStatusResponse)
def get_final_report_status(session_id: str) -> FinalReportStatusResponse:
    """세션의 최종 문서 생성 상태를 조회한다."""

    session_service = get_session_service()
    session = session_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    report_service = get_report_service()
    status = report_service.get_final_status(
        session_id=session_id,
        session_ended=session.ended_at is not None,
    )
    return FinalReportStatusResponse(
        session_id=status.session_id,
        status=status.status,
        report_count=status.report_count,
        latest_report_id=status.latest_report_id,
        latest_report_type=status.latest_report_type,
        latest_generated_at=status.latest_generated_at,
        latest_file_path=status.latest_file_path,
    )


@router.get("/{session_id}/{report_id}", response_model=LatestReportResponse)
def get_report_by_id(session_id: str, report_id: str) -> LatestReportResponse:
    """리포트 ID로 개별 리포트를 조회한다."""

    report_service = get_report_service()
    report = report_service.get_report_by_id(report_id)
    if report is None or report.session_id != session_id:
        raise HTTPException(status_code=404, detail="리포트를 찾을 수 없습니다.")
    return LatestReportResponse(
        id=report.id,
        session_id=report.session_id,
        report_type=report.report_type,
        version=report.version,
        file_path=report.file_path,
        insight_source=report.insight_source,
        generated_at=report.generated_at,
        content=report_service.read_report_content(report),
    )
