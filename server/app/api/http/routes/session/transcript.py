"""HTTP 계층에서 세션 관련 transcript 구성을 담당한다."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from server.app.api.http.access_control import get_accessible_session_or_raise
from server.app.api.http.schemas.meeting_session import (
    SessionTranscriptItemResponse,
    SessionTranscriptResponse,
)
from server.app.api.http.security import require_authenticated_session
from server.app.api.http.wiring.artifact_storage import get_local_artifact_store
from server.app.api.http.wiring.persistence import get_utterance_repository
from server.app.domain.models.auth_session import AuthenticatedSession
from server.app.services.reports.refinement import TranscriptCorrectionStore

router = APIRouter()


@router.get("/{session_id}/transcript", response_model=SessionTranscriptResponse)
def get_session_transcript(
    session_id: str,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> SessionTranscriptResponse:
    """세션 canonical transcript를 조회한다."""

    session = get_accessible_session_or_raise(session_id, auth_context)
    utterances = get_utterance_repository().list_by_session(session_id)
    correction_map = TranscriptCorrectionStore(
        get_local_artifact_store()
    ).load_map(
        session_id=session_id,
        expected_source_version=session.canonical_transcript_version,
    )
    return SessionTranscriptResponse(
        session_id=session.id,
        status=session.post_processing_status,
        canonical_transcript_version=session.canonical_transcript_version,
        items=[
            SessionTranscriptItemResponse(
                id=item.id,
                seq_num=item.seq_num,
                speaker_label=item.speaker_label,
                start_ms=item.start_ms,
                end_ms=item.end_ms,
                text=(
                    correction_map[item.id].corrected_text
                    if item.id in correction_map
                    else item.text
                ),
                raw_text=item.text,
                is_corrected=item.id in correction_map,
                confidence=item.confidence,
                input_source=item.input_source,
                transcript_source=item.transcript_source,
                processing_job_id=item.processing_job_id,
            )
            for item in utterances
        ],
    )
