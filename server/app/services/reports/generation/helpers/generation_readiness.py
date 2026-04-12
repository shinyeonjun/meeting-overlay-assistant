"""리포트 영역의 generation readiness 서비스를 제공한다."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)


@dataclass(frozen=True)
class ReportGenerationReadiness:
    """리포트 생성 전에 확인할 입력 상태 묶음."""

    audio_path: Path | None
    live_events: list
    transcript_lines: list[str]
    speaker_transcript: list[SpeakerTranscriptSegment]


def resolve_report_generation_readiness(
    *,
    session_id: str,
    audio_path: Path | None,
    event_repository,
    utterance_repository=None,
    transcript_correction_store=None,
) -> ReportGenerationReadiness:
    """녹음 파일 또는 저장된 transcript/event 존재 여부를 공통 규칙으로 판단한다."""

    resolved_audio_path = (
        audio_path
        if audio_path is not None and Path(audio_path).exists()
        else None
    )
    stored_events = event_repository.list_by_session(
        session_id,
        insight_scope="finalized",
    )
    if not stored_events:
        stored_events = event_repository.list_by_session(session_id)

    utterances = _list_utterances(
        session_id=session_id,
        utterance_repository=utterance_repository,
    )
    correction_map = (
        transcript_correction_store.load_map(session_id=session_id)
        if transcript_correction_store is not None
        else {}
    )
    transcript_lines = [
        _resolve_transcript_text(utterance, correction_map)
        for utterance in utterances
        if _resolve_transcript_text(utterance, correction_map)
    ]
    speaker_transcript = [
        SpeakerTranscriptSegment(
            speaker_label=utterance.speaker_label or "speaker-unknown",
            start_ms=utterance.start_ms,
            end_ms=utterance.end_ms,
            text=_resolve_transcript_text(utterance, correction_map),
            confidence=utterance.confidence,
        )
        for utterance in utterances
        if _resolve_transcript_text(utterance, correction_map)
    ]

    if resolved_audio_path is None and not stored_events and not transcript_lines:
        raise ValueError("리포트 생성에 필요한 녹음 파일 또는 저장된 transcript/event가 없습니다.")

    return ReportGenerationReadiness(
        audio_path=resolved_audio_path,
        live_events=stored_events,
        transcript_lines=transcript_lines,
        speaker_transcript=speaker_transcript,
    )


def _list_utterances(*, session_id: str, utterance_repository) -> list:
    if utterance_repository is None:
        return []
    return utterance_repository.list_by_session(session_id)


def _resolve_transcript_text(utterance, correction_map: dict) -> str:
    corrected = correction_map.get(utterance.id)
    if corrected is not None and corrected.corrected_text.strip():
        return corrected.corrected_text.strip()
    return utterance.text.strip()
