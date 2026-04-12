"""faster-whisper 기반 pseudo-streaming STT 구현."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace

from server.app.services.audio.stt.faster_whisper_speech_to_text_service import (
    FasterWhisperConfig,
    FasterWhisperSpeechToTextService,
)
from server.app.services.audio.stt.faster_whisper.streaming_logic import (
    build_preview_segment,
    compute_stable_preview,
    duration_ms_to_bytes,
    is_meaningful_growth,
    merge_with_previous_stable_preview,
    trim_buffer,
)
from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment
from server.app.services.audio.stt.common.preview_stability import (
    normalize_text,
)
from server.app.services.audio.stt.transcription import (
    StreamingSpeechToTextService,
    TranscriptionResult,
)


@dataclass(frozen=True)
class FasterWhisperStreamingConfig(FasterWhisperConfig):
    """faster-whisper pseudo-streaming 실행 설정."""

    partial_buffer_ms: int = 900
    partial_emit_interval_ms: int = 240
    partial_min_rms_threshold: float = 0.004
    partial_agreement_window: int = 2
    partial_agreement_min_count: int = 2
    partial_min_stable_chars: int = 4
    partial_min_growth_chars: int = 2
    partial_backtrack_tolerance_chars: int = 2
    partial_commit_min_chars_without_boundary: int = 6


class FasterWhisperStreamingSpeechToTextService(
    FasterWhisperSpeechToTextService,
    StreamingSpeechToTextService,
):
    """rolling buffer를 이용해 partial/final transcript를 만든다."""

    def __init__(self, config: FasterWhisperStreamingConfig) -> None:
        if config.initial_prompt:
            config = replace(config, initial_prompt=None)
        super().__init__(config)
        self._streaming_config = config
        self._buffer = bytearray()
        self._bytes_since_emit = 0
        self._preview_revision = 0
        self._last_emitted_preview = ""
        self._last_stable_preview = ""
        self._max_buffer_bytes = duration_ms_to_bytes(
            duration_ms=config.partial_buffer_ms,
            sample_rate_hz=config.sample_rate_hz,
            sample_width_bytes=config.sample_width_bytes,
            channels=config.channels,
        )
        self._emit_interval_bytes = duration_ms_to_bytes(
            duration_ms=config.partial_emit_interval_ms,
            sample_rate_hz=config.sample_rate_hz,
            sample_width_bytes=config.sample_width_bytes,
            channels=config.channels,
        )
        self._preview_history: deque[str] = deque(
            maxlen=max(config.partial_agreement_window, 1)
        )

    def preview_chunk(self, chunk: bytes) -> list[TranscriptionResult]:
        """입력 chunk를 기준으로 partial transcript 후보를 만든다."""

        if not chunk:
            return []

        self._buffer.extend(chunk)
        self._bytes_since_emit += len(chunk)
        self._trim_buffer()

        if self._bytes_since_emit < self._emit_interval_bytes:
            return []

        self._bytes_since_emit = 0
        preview_audio = bytes(self._buffer)
        if (
            self._compute_preview_rms(preview_audio)
            < self._streaming_config.partial_min_rms_threshold
        ):
            return []

        preview_segment = self._build_preview_segment(preview_audio)
        result = self._transcribe_preview_segment(preview_segment)
        normalized_text = normalize_text(result.text)
        if not normalized_text:
            return []

        self._preview_history.append(normalized_text)
        stable_preview = self._compute_stable_preview()
        if not stable_preview or stable_preview == self._last_emitted_preview:
            return []

        self._preview_revision += 1
        self._last_emitted_preview = stable_preview
        return [
            TranscriptionResult(
                text=stable_preview,
                confidence=result.confidence,
                kind="partial",
                revision=self._preview_revision,
                no_speech_prob=result.no_speech_prob,
            )
        ]

    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        """최종 세그먼트를 전사하고 preview 상태를 초기화한다."""

        result = super().transcribe(segment)
        self.reset_stream()
        return TranscriptionResult(
            text=result.text,
            confidence=result.confidence,
            kind="final",
            no_speech_prob=result.no_speech_prob,
        )

    def reset_stream(self) -> None:
        """stream 상태를 초기화한다."""

        self._buffer.clear()
        self._bytes_since_emit = 0
        self._preview_revision = 0
        self._last_emitted_preview = ""
        self._last_stable_preview = ""
        self._preview_history.clear()

    def _build_preview_segment(self, raw_bytes: bytes) -> SpeechSegment:
        return build_preview_segment(
            raw_bytes=raw_bytes,
            sample_rate_hz=self._streaming_config.sample_rate_hz,
            sample_width_bytes=self._streaming_config.sample_width_bytes,
            channels=self._streaming_config.channels,
        )

    def _transcribe_preview_segment(self, segment: SpeechSegment) -> TranscriptionResult:
        return super().transcribe(segment)

    def _duration_ms_to_bytes(self, duration_ms: int) -> int:
        return duration_ms_to_bytes(
            duration_ms=duration_ms,
            sample_rate_hz=self._streaming_config.sample_rate_hz,
            sample_width_bytes=self._streaming_config.sample_width_bytes,
            channels=self._streaming_config.channels,
        )

    def _trim_buffer(self) -> None:
        trim_buffer(self._buffer, max_buffer_bytes=self._max_buffer_bytes)

    def _compute_preview_rms(self, raw_bytes: bytes) -> float:
        audio = self._pcm16_to_float32_audio(raw_bytes)
        if audio.size == 0:
            return 0.0
        return self._compute_rms(audio)

    def _compute_stable_preview(self) -> str:
        stable_preview = compute_stable_preview(
            preview_history=list(self._preview_history),
            latest_preview=self._preview_history[-1],
            last_stable_preview=self._last_stable_preview,
            last_emitted_preview=self._last_emitted_preview,
            agreement_min_count=self._streaming_config.partial_agreement_min_count,
            min_stable_chars=self._streaming_config.partial_min_stable_chars,
            min_growth_chars=self._streaming_config.partial_min_growth_chars,
            backtrack_tolerance_chars=self._streaming_config.partial_backtrack_tolerance_chars,
            commit_min_chars_without_boundary=self._streaming_config.partial_commit_min_chars_without_boundary,
        )
        if not stable_preview:
            return ""

        self._last_stable_preview = stable_preview
        return stable_preview

    def _is_meaningful_growth(self, stable_preview: str) -> bool:
        return is_meaningful_growth(
            stable_preview=stable_preview,
            last_emitted_preview=self._last_emitted_preview,
            min_growth_chars=self._streaming_config.partial_min_growth_chars,
        )

    def _merge_with_previous_stable_preview(self, committed_preview: str) -> str:
        return merge_with_previous_stable_preview(
            committed_preview=committed_preview,
            last_stable_preview=self._last_stable_preview,
            backtrack_tolerance_chars=self._streaming_config.partial_backtrack_tolerance_chars,
        )
