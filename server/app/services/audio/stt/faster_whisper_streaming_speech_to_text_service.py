"""faster-whisper 기반 pseudo-streaming STT 구현."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace

from server.app.services.audio.stt.faster_whisper_speech_to_text_service import (
    FasterWhisperConfig,
    FasterWhisperSpeechToTextService,
)
from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment
from server.app.services.audio.stt.transcription import (
    StreamingSpeechToTextService,
    TranscriptionResult,
)

COMMIT_BOUNDARY_CHARS = {" ", ".", ",", "?", "!", ":", ";"}
COMPARISON_IGNORED_CHARS = COMMIT_BOUNDARY_CHARS | {"\n", "\t", '"', "'", "(", ")"}


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
        self._max_buffer_bytes = self._duration_ms_to_bytes(config.partial_buffer_ms)
        self._emit_interval_bytes = self._duration_ms_to_bytes(
            config.partial_emit_interval_ms
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
        normalized_text = self._normalize_text(result.text)
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
        frame_bytes = (
            self._streaming_config.sample_rate_hz
            * self._streaming_config.sample_width_bytes
            * self._streaming_config.channels
        )
        duration_ms = int(len(raw_bytes) / max(frame_bytes, 1) * 1000)
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

    def _compute_stable_preview(self) -> str:
        if len(self._preview_history) < self._streaming_config.partial_agreement_min_count:
            return ""

        significant_history = [
            self._significant_text(value) for value in self._preview_history if value
        ]
        if len(significant_history) < self._streaming_config.partial_agreement_min_count:
            return ""

        stable_significant = self._longest_common_prefix(significant_history)
        if len(stable_significant) < self._streaming_config.partial_min_stable_chars:
            return ""

        latest_preview = self._preview_history[-1]
        projected_preview = self._project_significant_prefix_to_text(
            latest_preview,
            len(stable_significant),
        )
        if not projected_preview:
            return ""

        committed_preview = self._trim_to_commit_boundary(
            projected_preview,
            self._streaming_config.partial_commit_min_chars_without_boundary,
        )
        if (
            len(self._significant_text(committed_preview))
            < self._streaming_config.partial_min_stable_chars
        ):
            return ""

        stable_preview = self._merge_with_previous_stable_preview(committed_preview)
        if (
            len(self._significant_text(stable_preview))
            < self._streaming_config.partial_min_stable_chars
        ):
            return ""

        self._last_stable_preview = stable_preview
        if not self._is_meaningful_growth(stable_preview):
            return ""

        return stable_preview

    def _is_meaningful_growth(self, stable_preview: str) -> bool:
        current_significant = self._significant_text(stable_preview)
        last_significant = self._significant_text(self._last_emitted_preview)
        if current_significant == last_significant:
            return False

        growth = len(current_significant) - len(last_significant)
        if growth >= self._streaming_config.partial_min_growth_chars:
            return True

        if growth >= 0 and current_significant.startswith(last_significant):
            return True

        return False

    def _merge_with_previous_stable_preview(self, committed_preview: str) -> str:
        if not self._last_stable_preview:
            return committed_preview

        previous_significant = self._significant_text(self._last_stable_preview)
        current_significant = self._significant_text(committed_preview)

        if current_significant.startswith(previous_significant):
            return committed_preview

        overlap = self._longest_common_prefix(
            [previous_significant, current_significant]
        )
        backtrack = len(previous_significant) - len(overlap)
        if backtrack <= self._streaming_config.partial_backtrack_tolerance_chars:
            return self._last_stable_preview

        return committed_preview

    @staticmethod
    def _normalize_text(text: str) -> str:
        return " ".join(text.casefold().split())

    @staticmethod
    def _longest_common_prefix(values: list[str]) -> str:
        if not values:
            return ""

        prefix = values[0]
        for candidate in values[1:]:
            limit = min(len(prefix), len(candidate))
            index = 0
            while index < limit and prefix[index] == candidate[index]:
                index += 1
            prefix = prefix[:index]
            if not prefix:
                break
        return prefix

    @staticmethod
    def _trim_to_commit_boundary(text: str, minimum_without_boundary: int) -> str:
        """한국어처럼 공백이 적은 문장은 내부 구두점보다 안정 길이를 우선한다."""

        if not text:
            return ""

        trimmed = text.strip()
        if not trimmed:
            return ""

        significant_text = (
            FasterWhisperStreamingSpeechToTextService._significant_text(trimmed)
        )
        if len(significant_text) >= minimum_without_boundary:
            return trimmed

        if trimmed[-1] in COMMIT_BOUNDARY_CHARS:
            return trimmed

        last_boundary = -1
        for boundary_char in COMMIT_BOUNDARY_CHARS:
            last_boundary = max(last_boundary, trimmed.rfind(boundary_char))

        if last_boundary > 0:
            return trimmed[:last_boundary].strip()
        return ""

    @staticmethod
    def _significant_text(text: str) -> str:
        return "".join(
            char
            for char in text
            if char not in COMPARISON_IGNORED_CHARS and not char.isspace()
        )

    @staticmethod
    def _project_significant_prefix_to_text(text: str, significant_length: int) -> str:
        if significant_length <= 0:
            return ""

        significant_seen = 0
        last_index = -1
        for index, char in enumerate(text):
            if char in COMPARISON_IGNORED_CHARS or char.isspace():
                continue
            significant_seen += 1
            last_index = index
            if significant_seen >= significant_length:
                break

        if last_index < 0:
            return ""

        return text[: last_index + 1].rstrip()

