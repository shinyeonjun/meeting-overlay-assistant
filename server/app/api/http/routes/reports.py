"""리포트 라우트 호환 facade."""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException

from server.app.api.http.dependencies import (
    get_report_generation_job_service,
    get_report_service,
    get_report_share_service,
)
from server.app.api.http.routes.report.router import router
from server.app.services.audio.io.session_recording import find_session_recording_path


def _resolve_audio_path(session_id: str, audio_path: str | None) -> Path | None:
    """명시적 audio_path 또는 세션 녹음 파일 경로를 해석한다."""

    if audio_path:
        return Path(audio_path)
    return find_session_recording_path(session_id)


def _get_report_or_404(*, session_id: str, report_id: str):
    """세션 소속 리포트를 강제 조회한다."""

    report = get_report_service().get_report_by_id(report_id)
    if report is None or report.session_id != session_id:
        raise HTTPException(status_code=404, detail="리포트를 찾을 수 없습니다.")
    return report


def get_report_job_service():
    """리포트 생성 job 서비스를 반환한다."""

    return get_report_generation_job_service()
