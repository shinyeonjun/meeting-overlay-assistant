"""리포트 생성 입력 준비 상태를 판단하는 helper."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from server.app.domain.models.speaker_names import (
    UNASSIGNED_SPEAKER_LABEL,
    normalize_speaker_label,
)
from server.app.domain.models.utterance import Utterance, select_visible_utterances
from server.app.contexts.reporting.application.audio.audio_postprocessing_service import (
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
    speaker_name_resolver: Callable[[str, list[Utterance]], dict[str, str]] | None = None,
) -> ReportGenerationReadiness:
    """녹음 파일 또는 저장된 transcript/event 존재 여부를 공통 규칙으로 판단한다.

    speaker_name_resolver가 있으면 리포트에 들어가는 화자 라벨을 화면과 같은 표시 이름
    (화자 1, 사용자가 붙인 이름)으로 바꾼다.
    """

    resolved_audio_path = audio_path if audio_path is not None and Path(audio_path).exists() else None
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
        transcript_correction_store.load_map(session_id=session_id) if transcript_correction_store is not None else {}
    )
    transcript_lines = [
        _resolve_transcript_text(utterance, correction_map)
        for utterance in utterances
        if _resolve_transcript_text(utterance, correction_map)
    ]
    speaker_names = (
        speaker_name_resolver(session_id, utterances) if speaker_name_resolver is not None and utterances else {}
    )
    stored_events = _rename_event_speakers(stored_events, speaker_names)
    speaker_transcript = [
        SpeakerTranscriptSegment(
            speaker_label=_resolve_speaker_name(utterance.speaker_label, speaker_names),
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
    return select_visible_utterances(utterance_repository.list_by_session(session_id))


def _resolve_speaker_name(speaker_label: str | None, speaker_names: dict[str, str]) -> str:
    label = normalize_speaker_label(speaker_label)
    return speaker_names.get(label, speaker_label or UNASSIGNED_SPEAKER_LABEL)


def _rename_event_speakers(events: list, speaker_names: dict[str, str]) -> list:
    # 화자가 없는 이벤트는 그대로 둔다. 누가 말했는지 모르는 이벤트를 특정 화자로 돌리지 않는다.
    if not speaker_names:
        return events
    return [
        replace(event, speaker_label=speaker_names.get(event.speaker_label, event.speaker_label))
        if event.speaker_label
        else event
        for event in events
    ]


def _resolve_transcript_text(utterance, correction_map: dict) -> str:
    corrected = correction_map.get(utterance.id)
    if corrected is not None and corrected.corrected_text.strip():
        return corrected.corrected_text.strip()
    return utterance.text.strip()
