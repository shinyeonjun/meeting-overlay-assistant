"""STT 공통 모델과 인터페이스."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment


@dataclass(frozen=True)
class TranscriptionResult:
    """STT 결과."""

    text: str
    confidence: float
    kind: str = "final"
    revision: int | None = None
    no_speech_prob: float | None = None
    stability: str | None = None


_preview_session_id_var: ContextVar[str | None] = ContextVar(
    "preview_session_id",
    default=None,
)
_preview_runtime_monitor_var: ContextVar[Any | None] = ContextVar(
    "preview_runtime_monitor",
    default=None,
)
_preview_cycle_id_var: ContextVar[int | None] = ContextVar(
    "preview_cycle_id",
    default=None,
)


def push_preview_runtime_context(
    *,
    session_id: str,
    runtime_monitor_service: Any | None,
    preview_cycle_id: int | None = None,
) -> tuple[Token[str | None], Token[Any | None], Token[int | None]]:
    """preview 처리 중 사용할 세션/모니터 컨텍스트를 저장한다."""

    return (
        _preview_session_id_var.set(session_id),
        _preview_runtime_monitor_var.set(runtime_monitor_service),
        _preview_cycle_id_var.set(preview_cycle_id),
    )


def pop_preview_runtime_context(
    tokens: tuple[Token[str | None], Token[Any | None], Token[int | None]],
) -> None:
    """preview 처리 컨텍스트를 원래 상태로 복원한다."""

    session_token, monitor_token, cycle_token = tokens
    _preview_session_id_var.reset(session_token)
    _preview_runtime_monitor_var.reset(monitor_token)
    _preview_cycle_id_var.reset(cycle_token)


def record_current_preview_stage(stage: str) -> None:
    """현재 preview 컨텍스트 기준으로 단계 이벤트를 기록한다."""

    session_id = _preview_session_id_var.get()
    runtime_monitor_service = _preview_runtime_monitor_var.get()
    if not session_id or runtime_monitor_service is None:
        return
    recorder = getattr(runtime_monitor_service, "record_preview_stage", None)
    if callable(recorder):
        recorder(
            session_id=session_id,
            stage=stage,
            preview_cycle_id=_preview_cycle_id_var.get(),
        )


@runtime_checkable
class SpeechToTextService(Protocol):
    """발화 구간을 텍스트로 변환하는 STT 인터페이스."""

    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        """세그먼트를 텍스트로 변환한다."""


@runtime_checkable
class StreamingSpeechToTextService(Protocol):
    """실시간 partial transcript를 지원하는 STT 인터페이스."""

    def preview_chunk(self, chunk: bytes) -> list[TranscriptionResult]:
        """입력 chunk 기준으로 partial transcript를 생성한다."""

    def reset_stream(self) -> None:
        """스트리밍 상태를 초기화한다."""
