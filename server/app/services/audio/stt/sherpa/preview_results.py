"""오디오 영역의 preview results 서비스를 제공한다."""
from __future__ import annotations

from server.app.services.audio.stt.common.preview_stability import normalize_text
from server.app.services.audio.stt.sherpa.state import SherpaStreamingState
from server.app.services.audio.stt.transcription import TranscriptionResult


def append_preview_result(
    *,
    state: SherpaStreamingState,
    current_text: str,
    normalized_text: str,
    results: list[TranscriptionResult],
) -> None:
    """의미 있는 preview 변경이 있으면 결과에 추가한다."""

    if normalized_text == normalize_text(state.last_preview_text):
        return

    state.preview_revision += 1
    state.last_preview_text = current_text
    state.last_partial_text = current_text
    results.append(
        TranscriptionResult(
            text=current_text,
            confidence=0.55,
            kind="preview",
            revision=state.preview_revision,
            stability="low",
        )
    )


def append_live_final_result(
    *,
    state: SherpaStreamingState,
    stable_preview: str,
    results: list[TranscriptionResult],
) -> None:
    """안정화된 preview가 있으면 live_final 결과를 추가한다."""

    if not stable_preview or stable_preview == state.last_emitted_live_final:
        return

    state.preview_revision += 1
    state.last_emitted_live_final = stable_preview
    state.last_emitted_preview = stable_preview
    results.append(
        TranscriptionResult(
            text=stable_preview,
            confidence=0.7,
            kind="live_final",
            revision=state.preview_revision,
            stability="medium",
        )
    )
