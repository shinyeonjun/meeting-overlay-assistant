"""오디오 영역의 state 서비스를 제공한다."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass
class SherpaStreamingState:
    """preview/live_final 생성에 필요한 가변 상태."""

    preview_revision: int = 0
    last_preview_text: str = ""
    last_partial_text: str = ""
    last_emitted_live_final: str = ""
    last_emitted_preview: str = ""
    last_stable_preview: str = ""
    bytes_since_emit: int = 0
    preview_history: deque[str] = field(default_factory=deque)


def create_streaming_state(*, history_size: int) -> SherpaStreamingState:
    """history 길이를 반영한 기본 streaming 상태를 만든다."""

    return SherpaStreamingState(preview_history=deque(maxlen=max(history_size, 1)))


def reset_streaming_state(state: SherpaStreamingState) -> None:
    """streaming 상태를 초기값으로 되돌린다."""

    state.preview_revision = 0
    state.last_preview_text = ""
    state.last_partial_text = ""
    state.last_emitted_live_final = ""
    state.last_emitted_preview = ""
    state.last_stable_preview = ""
    state.bytes_since_emit = 0
    state.preview_history.clear()
