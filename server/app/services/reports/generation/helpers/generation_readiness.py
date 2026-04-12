"""리포트 생성 입력 가능 여부를 판단하는 공통 helper."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReportGenerationReadiness:
    """리포트 생성 전에 확인한 입력 상태를 묶는다."""

    audio_path: Path | None
    live_events: list
    transcript_lines: list[str]


def resolve_report_generation_readiness(
    *,
    session_id: str,
    audio_path: Path | None,
    event_repository,
    utterance_repository=None,
) -> ReportGenerationReadiness:
    """녹음 또는 live transcript/event가 있는지 공통 정책으로 판단한다."""

    resolved_audio_path = (
        audio_path
        if audio_path is not None and Path(audio_path).exists()
        else None
    )
    live_events = event_repository.list_by_session(
        session_id,
        insight_scope="live",
    )
    transcript_lines = _build_transcript_lines(
        session_id=session_id,
        utterance_repository=utterance_repository,
    )

    if resolved_audio_path is None and not live_events and not transcript_lines:
        raise ValueError("리포트 생성에 필요한 녹음 파일 또는 live transcript/event가 없습니다.")

    return ReportGenerationReadiness(
        audio_path=resolved_audio_path,
        live_events=live_events,
        transcript_lines=transcript_lines,
    )


def _build_transcript_lines(*, session_id: str, utterance_repository) -> list[str]:
    if utterance_repository is None:
        return []

    utterances = utterance_repository.list_by_session(session_id)
    return [utterance.text.strip() for utterance in utterances if utterance.text.strip()]
