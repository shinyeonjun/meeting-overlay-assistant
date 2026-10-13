"""세션 canonical transcript와 화자 이름 라우트."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from server.app.api.http.access_control import get_accessible_session_or_raise
from server.app.api.http.dependencies import get_speaker_name_service
from server.app.api.http.schemas.meeting_session import (
    SessionSpeakerItemResponse,
    SessionSpeakerNameUpdateRequest,
    SessionSpeakersResponse,
    SessionTranscriptItemResponse,
    SessionTranscriptResponse,
)
from server.app.api.http.security import require_authenticated_session
from server.app.api.http.wiring.artifact_storage import get_local_artifact_store
from server.app.api.http.wiring.persistence import get_utterance_repository
from server.app.contexts.identity import AuthenticatedRequest
from server.app.contexts.meeting import SpeakerNamesLockedError, SpeakerNotFoundError
from server.app.domain.models.speaker_names import (
    MAX_SPEAKER_NAME_LENGTH,
    normalize_speaker_label,
)
from server.app.domain.models.utterance import select_visible_utterances
from server.app.contexts.reporting import TranscriptCorrectionStore

router = APIRouter()


def _load_visible_utterances(session):
    # 후처리 중에는 진행 상황(draft)을, 그 외에는 draft를 뺀 정본을 보여준다.
    return select_visible_utterances(
        get_utterance_repository().list_by_session(session.id),
        prefer_drafts=session.post_processing_status == "processing",
    )


def _to_speakers_response(session, summaries) -> SessionSpeakersResponse:
    return SessionSpeakersResponse(
        session_id=session.id,
        canonical_transcript_version=session.canonical_transcript_version,
        max_name_length=MAX_SPEAKER_NAME_LENGTH,
        items=[
            SessionSpeakerItemResponse(
                speaker_label=summary.speaker_label,
                display_name=summary.display_name,
                default_name=summary.default_name,
                custom_name=summary.custom_name,
                utterance_count=summary.utterance_count,
            )
            for summary in summaries
        ],
    )


@router.get("/{session_id}/transcript", response_model=SessionTranscriptResponse)
def get_session_transcript(
    session_id: str,
    auth_context: AuthenticatedRequest | None = Depends(require_authenticated_session),
) -> SessionTranscriptResponse:
    """세션 canonical transcript를 조회한다."""

    session = get_accessible_session_or_raise(session_id, auth_context)
    utterances = _load_visible_utterances(session)
    speaker_names = get_speaker_name_service().build_name_map(session, utterances)
    correction_map = TranscriptCorrectionStore(get_local_artifact_store()).load_map(
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
                speaker_name=speaker_names.get(normalize_speaker_label(item.speaker_label)),
                start_ms=item.start_ms,
                end_ms=item.end_ms,
                text=(correction_map[item.id].corrected_text if item.id in correction_map else item.text),
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


@router.get("/{session_id}/speakers", response_model=SessionSpeakersResponse)
def get_session_speakers(
    session_id: str,
    auth_context: AuthenticatedRequest | None = Depends(require_authenticated_session),
) -> SessionSpeakersResponse:
    """회의 기록의 화자 목록과 표시 이름을 조회한다."""

    session = get_accessible_session_or_raise(session_id, auth_context)
    summaries = get_speaker_name_service().list_speakers(
        session,
        _load_visible_utterances(session),
    )
    return _to_speakers_response(session, summaries)


@router.put("/{session_id}/speakers", response_model=SessionSpeakersResponse)
def update_session_speaker_name(
    session_id: str,
    request: SessionSpeakerNameUpdateRequest,
    auth_context: AuthenticatedRequest | None = Depends(require_authenticated_session),
) -> SessionSpeakersResponse:
    """화자 라벨에 이름을 붙인다. 같은 라벨의 모든 발화에 적용된다."""

    session = get_accessible_session_or_raise(session_id, auth_context)
    try:
        summaries = get_speaker_name_service().rename(
            session,
            _load_visible_utterances(session),
            speaker_label=request.speaker_label,
            display_name=request.display_name,
        )
    except SpeakerNamesLockedError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except SpeakerNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return _to_speakers_response(session, summaries)
