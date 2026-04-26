"""리포트 artifact 다운로드/미리보기 라우트."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from server.app.api.http.access_control import get_accessible_session_or_raise
from server.app.api.http.security import require_authenticated_session
from server.app.domain.models.auth_session import AuthenticatedSession

router = APIRouter()

_ARTIFACT_SUFFIXES = {
    "source": None,
    "html": "html",
    "document": "document.json",
    "transcript": "transcript.md",
    "analysis": "analysis.json",
}

_MEDIA_TYPES = {
    "html": "text/html; charset=utf-8",
    "document": "application/json",
    "transcript": "text/markdown; charset=utf-8",
    "analysis": "application/json",
    ".md": "text/markdown; charset=utf-8",
    ".pdf": "application/pdf",
}


def _reports_facade():
    from server.app.api.http import routes as api_routes

    return api_routes.reports


@router.get("/{session_id}/{report_id}/artifact/{artifact_kind}")
def get_report_artifact(
    session_id: str,
    report_id: str,
    artifact_kind: str,
    download: bool = Query(default=False),
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> FileResponse:
    """리포트 본문과 부가 artifact를 파일 응답으로 제공한다."""

    get_accessible_session_or_raise(session_id, auth_context)
    report = _reports_facade()._get_report_or_404(
        session_id=session_id,
        report_id=report_id,
    )
    artifact_path = _resolve_report_artifact_path(report, artifact_kind)
    media_type = _resolve_media_type(artifact_kind, artifact_path)
    disposition = "attachment" if download else "inline"
    return FileResponse(
        artifact_path,
        media_type=media_type,
        filename=artifact_path.name,
        headers={"Content-Disposition": f'{disposition}; filename="{artifact_path.name}"'},
    )


def _resolve_report_artifact_path(report, artifact_kind: str) -> Path:
    normalized_kind = artifact_kind.strip().lower()
    if normalized_kind not in _ARTIFACT_SUFFIXES:
        raise HTTPException(status_code=404, detail="지원하지 않는 리포트 artifact입니다.")

    report_service = _reports_facade().get_report_service()
    report_path = report_service.resolve_report_path(report)
    if report_path is None or not report_path.exists():
        raise HTTPException(status_code=404, detail="리포트 파일을 찾을 수 없습니다.")

    if normalized_kind == "source":
        return report_path

    suffix = _ARTIFACT_SUFFIXES[normalized_kind]
    artifact_path = report_path.parent / "artifacts" / f"{report_path.stem}.{suffix}"
    if not artifact_path.exists():
        raise HTTPException(status_code=404, detail="리포트 artifact를 찾을 수 없습니다.")
    return artifact_path


def _resolve_media_type(artifact_kind: str, artifact_path: Path) -> str:
    normalized_kind = artifact_kind.strip().lower()
    if normalized_kind in _MEDIA_TYPES:
        return _MEDIA_TYPES[normalized_kind]
    return _MEDIA_TYPES.get(artifact_path.suffix.lower(), "application/octet-stream")
