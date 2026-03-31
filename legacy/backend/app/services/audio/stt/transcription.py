"""STT 공통 모델과 인터페이스."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from backend.app.services.audio.segmentation.speech_segmenter import SpeechSegment


@dataclass(frozen=True)
class TranscriptionResult:
    """STT 결과."""

    text: str
    confidence: float
    kind: str = "final"
    revision: int | None = None
    no_speech_prob: float | None = None
    stability: str | None = None


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

