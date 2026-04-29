"""회의록 정본 문서 편집 라우트."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from server.app.api.http.access_control import get_accessible_session_or_raise
from server.app.api.http.schemas.report import (
    PdfReportResponse,
    ReportDocumentResponse,
    ReportDocumentUpdateRequest,
)
from server.app.api.http.security import require_authenticated_session
from server.app.core.config import ROOT_DIR
from server.app.domain.models.auth_session import AuthenticatedSession
from server.app.services.reports.composition.report_document import (
    REPORT_DOCUMENT_VERSION,
    report_document_from_dict,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _reports_facade():
    from server.app.api.http import routes as api_routes

    return api_routes.reports


@router.get("/{session_id}/{report_id}/document", response_model=ReportDocumentResponse)
def get_report_document(
    session_id: str,
    report_id: str,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> ReportDocumentResponse:
    """회의록 편집에 사용할 정본 document artifact를 조회한다."""

    get_accessible_session_or_raise(session_id, auth_context)
    report = _reports_facade()._get_report_or_404(
        session_id=session_id,
        report_id=report_id,
    )
    report_service = _reports_facade().get_report_service()
    try:
        payload = report_service.load_report_document_payload(report)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="회의록 편집 데이터를 찾을 수 없습니다.") from error
    except ValueError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    document = payload.get("document")
    if not isinstance(document, dict):
        raise HTTPException(status_code=500, detail="회의록 편집 데이터 형식이 올바르지 않습니다.")

    template_version = str(payload.get("template_version") or REPORT_DOCUMENT_VERSION)
    return ReportDocumentResponse(
        template_version=template_version,
        document=document,
    )


@router.post("/{session_id}/{report_id}/document", response_model=PdfReportResponse)
def update_report_document(
    session_id: str,
    report_id: str,
    request: ReportDocumentUpdateRequest,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> PdfReportResponse:
    """편집된 정본 문서로 새 PDF 회의록 버전을 생성한다."""

    get_accessible_session_or_raise(session_id, auth_context)
    _reports_facade()._get_report_or_404(
        session_id=session_id,
        report_id=report_id,
    )
    try:
        document = report_document_from_dict({"document": request.document})
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    report_service = _reports_facade().get_report_service()
    output_dir = ROOT_DIR / "server" / "data" / "reports"
    result = report_service.build_edited_pdf_report(
        session_id=session_id,
        output_dir=Path(output_dir),
        document=document,
        generated_by_user_id=auth_context.user.id if auth_context is not None else None,
        source_report_id=report_id,
    )
    _try_index_edited_report(result)
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
        document_path=result.document_path,
    )


def _try_index_edited_report(result) -> None:
    indexing_service = _reports_facade().get_report_knowledge_indexing_service()
    if indexing_service is None:
        return
    try:
        indexing_service.index_pdf_report_source_markdown(result)
    except Exception:
        logger.exception(
            "편집 회의록 knowledge 인덱싱 실패: session_id=%s report_id=%s",
            result.report.session_id,
            result.report.id,
        )
