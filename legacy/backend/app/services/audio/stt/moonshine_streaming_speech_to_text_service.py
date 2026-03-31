"""Moonshine 기반 pseudo-streaming STT 구현."""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.services.audio.stt.moonshine_speech_to_text_service import (
    MoonshineConfig,
    MoonshineSpeechToTextService,
)
from backend.app.services.audio.segmentation.speech_segmenter import SpeechSegment
from backend.app.services.audio.stt.transcription import (
    StreamingSpeechToTextService,
    TranscriptionResult,
)


@dataclass(frozen=True)
class MoonshineStreamingConfig(MoonshineConfig):
    """Moonshine streaming 실행 설정."""

    partial_buffer_ms: int = 900
    partial_emit_interval_ms: int = 240
    partial_min_rms_threshold: float = 0.004
    partial_agreement_window: int = 2
    partial_agreement_min_count: int = 2
    partial_min_stable_chars: int = 4
    partial_min_growth_chars: int = 2


class MoonshineStreamingSpeechToTextService(
    MoonshineSpeechToTextService,
    StreamingSpeechToTextService,
):
    """짧은 sliding window로 partial transcript를 생성하는 Moonshine 구현."""

    def __init__(self, config: MoonshineStreamingConfig) -> None:
        super().__init__(config)
        self._streaming_config = config
        self._buffer = bytearray()
        self._bytes_since_emit = 0
        self._preview_revision = 0
        self._last_preview_text = ""
        self._max_buffer_bytes = self._duration_ms_to_bytes(config.partial_buffer_ms)
        self._emit_interval_bytes = self._duration_ms_to_bytes(config.partial_emit_interval_ms)

    def preview_chunk(self, chunk: bytes) -> list[TranscriptionResult]:
        """현재 chunk를 반영한 partial transcript를 생성한다."""

        if not chunk:
            return []

        self._buffer.extend(chunk)
        self._bytes_since_emit += len(chunk)
        self._trim_buffer()

        if self._bytes_since_emit < self._emit_interval_bytes:
            return []

        self._bytes_since_emit = 0
        preview_audio = bytes(self._buffer)
        preview_segment = self._build_preview_segment(preview_audio)

        if self._compute_preview_rms(preview_audio) < self._streaming_config.partial_min_rms_threshold:
            return []

        result = self._transcribe_preview_segment(preview_segment)
        normalized_text = self._normalize_text(result.text)
        if not normalized_text:
            return []
        if normalized_text == self._normalize_text(self._last_preview_text):
            return []

        self._preview_revision += 1
        self._last_preview_text = result.text
        return [
            TranscriptionResult(
                text=result.text,
                confidence=result.confidence,
                kind="partial",
                revision=self._preview_revision,
            )
        ]

    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        """최종 세그먼트 전사를 수행하고 스트리밍 상태를 초기화한다."""

        result = super().transcribe(segment)
        self.reset_stream()
        return TranscriptionResult(
            text=result.text,
            confidence=result.confidence,
            kind="final",
        )

    def reset_stream(self) -> None:
        """스트리밍 상태를 초기화한다."""

        self._buffer.clear()
        self._bytes_since_emit = 0
        self._preview_revision = 0
        self._last_preview_text = ""

    def _build_preview_segment(self, raw_bytes: bytes) -> SpeechSegment:
        duration_ms = int(
            len(raw_bytes)
            / (
                self._streaming_config.sample_rate_hz
                * self._streaming_config.sample_width_bytes
                * self._streaming_config.channels
            )
            * 1000
        )
        return SpeechSegment(
            start_ms=0,
            end_ms=max(duration_ms, 1),
            raw_bytes=raw_bytes,
        )

    def _transcribe_preview_segment(self, segment: SpeechSegment) -> TranscriptionResult:
        return super().transcribe(segment)

    def _duration_ms_to_bytes(self, duration_ms: int) -> int:
        bytes_per_second = (
            self._streaming_config.sample_rate_hz
            * self._streaming_config.sample_width_bytes
            * self._streaming_config.channels
        )
        return max(int(bytes_per_second * (duration_ms / 1000.0)), 1)

    def _trim_buffer(self) -> None:
        overflow = len(self._buffer) - self._max_buffer_bytes
        if overflow > 0:
            del self._buffer[:overflow]

    def _compute_preview_rms(self, raw_bytes: bytes) -> float:
        audio = self._pcm16_to_float32_audio(raw_bytes)
        if audio.size == 0:
            return 0.0
        return self._compute_rms(audio)

    @staticmethod
    def _normalize_text(text: str) -> str:
        return " ".join(text.casefold().split())

