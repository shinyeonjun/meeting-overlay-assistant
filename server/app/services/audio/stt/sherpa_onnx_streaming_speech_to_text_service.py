"""sherpa-onnx 기반 로컬 streaming STT 서비스."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path

from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment
from server.app.services.audio.stt.transcription import (
    StreamingSpeechToTextService,
    TranscriptionResult,
)

COMMIT_BOUNDARY_CHARS = {" ", ".", ",", "?", "!", ":", ";"}
COMPARISON_IGNORED_CHARS = COMMIT_BOUNDARY_CHARS | {"\n", "\t", '"', "'", "(", ")"}


@dataclass(frozen=True)
class SherpaOnnxStreamingConfig:
    """sherpa-onnx streaming 설정."""

    model_path: Path
    language: str | None = "ko"
    provider: str = "cpu"
    num_threads: int = 2
    sample_rate_hz: int = 16000
    sample_width_bytes: int = 2
    channels: int = 1
    decoding_method: str = "modified_beam_search"
    max_active_paths: int = 4
    enable_endpoint_detection: bool = False
    rule1_min_trailing_silence: float = 2.4
    rule2_min_trailing_silence: float = 0.6
    rule3_min_utterance_length: float = 8.0
    partial_emit_interval_ms: int = 220
    partial_agreement_window: int = 3
    partial_agreement_min_count: int = 2
    partial_min_stable_chars: int = 4
    partial_min_growth_chars: int = 2
    partial_backtrack_tolerance_chars: int = 2
    partial_commit_min_chars_without_boundary: int = 4


class SherpaOnnxStreamingSpeechToTextService(StreamingSpeechToTextService):
    """빠른 partial 생성을 위한 sherpa-onnx streaming 구현."""

    def __init__(self, config: SherpaOnnxStreamingConfig) -> None:
        self._config = config
        self._recognizer = self._create_recognizer(config)
        self._stream = self._recognizer.create_stream()
        self._preview_revision = 0
        self._last_partial_text = ""
        self._last_emitted_preview = ""
        self._last_stable_preview = ""
        self._bytes_since_emit = 0
        self._emit_interval_bytes = self._duration_ms_to_bytes(
            config.partial_emit_interval_ms
        )
        self._preview_history: deque[str] = deque(
            maxlen=max(config.partial_agreement_window, 1)
        )

    def preview_chunk(self, chunk: bytes) -> list[TranscriptionResult]:
        if not chunk:
            return []

        self._stream.accept_waveform(
            self._config.sample_rate_hz,
            self._pcm16_to_float32_audio(chunk),
        )
        self._bytes_since_emit += len(chunk)

        while self._recognizer.is_ready(self._stream):
            self._recognizer.decode_stream(self._stream)

        if self._bytes_since_emit < self._emit_interval_bytes:
            return []
        self._bytes_since_emit = 0

        current_text = self._recognizer.get_result(self._stream).strip()
        normalized_text = self._normalize_text(current_text)
        if not normalized_text:
            return []

        self._last_partial_text = current_text
        self._preview_history.append(normalized_text)
        stable_preview = self._compute_stable_preview(current_text)
        if not stable_preview or stable_preview == self._last_emitted_preview:
            return []

        self._preview_revision += 1
        self._last_emitted_preview = stable_preview
        return [
            TranscriptionResult(
                text=stable_preview,
                confidence=0.7,
                kind="fast_final",
                revision=self._preview_revision,
                stability="medium",
            )
        ]

    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        stream = self._recognizer.create_stream()
        stream.accept_waveform(
            self._config.sample_rate_hz,
            self._pcm16_to_float32_audio(segment.raw_bytes),
        )
        stream.input_finished()

        while self._recognizer.is_ready(stream):
            self._recognizer.decode_stream(stream)

        return TranscriptionResult(
            text=self._recognizer.get_result(stream).strip(),
            confidence=0.8,
            kind="final",
        )

    def reset_stream(self) -> None:
        self._stream = self._recognizer.create_stream()
        self._preview_revision = 0
        self._last_partial_text = ""
        self._last_emitted_preview = ""
        self._last_stable_preview = ""
        self._bytes_since_emit = 0
        self._preview_history.clear()

    @classmethod
    def _create_recognizer(cls, config: SherpaOnnxStreamingConfig):
        try:
            import sherpa_onnx
        except ImportError as error:  # pragma: no cover - 런타임 의존성
            raise RuntimeError("sherpa_onnx_streaming backend를 사용하려면 sherpa-onnx 패키지가 필요합니다.") from error

        artifacts = cls._resolve_transducer_artifacts(config.model_path)
        return sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=str(artifacts["tokens"]),
            encoder=str(artifacts["encoder"]),
            decoder=str(artifacts["decoder"]),
            joiner=str(artifacts["joiner"]),
            num_threads=config.num_threads,
            sample_rate=config.sample_rate_hz,
            provider=config.provider,
            decoding_method=config.decoding_method,
            max_active_paths=config.max_active_paths,
            enable_endpoint_detection=config.enable_endpoint_detection,
            rule1_min_trailing_silence=config.rule1_min_trailing_silence,
            rule2_min_trailing_silence=config.rule2_min_trailing_silence,
            rule3_min_utterance_length=config.rule3_min_utterance_length,
        )

    @classmethod
    def _resolve_transducer_artifacts(cls, model_dir: Path) -> dict[str, Path]:
        candidates = {
            "tokens": ("tokens.txt",),
            "encoder": ("encoder*.onnx",),
            "decoder": ("decoder*.onnx",),
            "joiner": ("joiner*.onnx",),
        }
        resolved: dict[str, Path] = {}
        for key, patterns in candidates.items():
            for pattern in patterns:
                matches = cls._sort_artifact_matches(key, model_dir.glob(pattern))
                if matches:
                    resolved[key] = matches[0].resolve()
                    break
            if key not in resolved:
                raise RuntimeError(f"sherpa-onnx 모델 파일을 찾지 못했습니다: key={key} dir={model_dir}")
        return resolved

    @staticmethod
    def _sort_artifact_matches(key: str, matches) -> list[Path]:
        paths = [path.resolve() for path in matches]

        def sort_key(path: Path) -> tuple[int, str]:
            name = path.name.casefold()
            is_int8 = ".int8." in name
            if key == "decoder":
                return (1 if is_int8 else 0, name)
            if key in {"encoder", "joiner"}:
                return (0 if is_int8 else 1, name)
            return (0, name)

        return sorted(paths, key=sort_key)

    def _compute_stable_preview(self, latest_text: str) -> str:
        if len(self._preview_history) < self._config.partial_agreement_min_count:
            return ""

        significant_history = [
            self._significant_text(value) for value in self._preview_history if value
        ]
        if len(significant_history) < self._config.partial_agreement_min_count:
            return ""

        stable_significant = self._longest_common_prefix(significant_history)
        if len(stable_significant) < self._config.partial_min_stable_chars:
            return ""

        projected_preview = self._project_significant_prefix_to_text(
            latest_text,
            len(stable_significant),
        )
        if not projected_preview:
            return ""

        committed_preview = self._trim_to_commit_boundary(
            projected_preview,
            self._config.partial_commit_min_chars_without_boundary,
        )
        if (
            len(self._significant_text(committed_preview))
            < self._config.partial_min_stable_chars
        ):
            return ""

        stable_preview = self._merge_with_previous_stable_preview(committed_preview)
        if not self._is_meaningful_growth(stable_preview):
            return ""

        self._last_stable_preview = stable_preview
        return stable_preview

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
        if backtrack <= self._config.partial_backtrack_tolerance_chars:
            return self._last_stable_preview

        return committed_preview

    def _is_meaningful_growth(self, stable_preview: str) -> bool:
        current_significant = self._significant_text(stable_preview)
        last_significant = self._significant_text(self._last_emitted_preview)
        if current_significant == last_significant:
            return False

        growth = len(current_significant) - len(last_significant)
        if growth >= self._config.partial_min_growth_chars:
            return True

        return growth >= 0 and current_significant.startswith(last_significant)

    def _duration_ms_to_bytes(self, duration_ms: int) -> int:
        bytes_per_second = (
            self._config.sample_rate_hz
            * self._config.sample_width_bytes
            * self._config.channels
        )
        return max(int(bytes_per_second * (duration_ms / 1000.0)), 1)

    def _pcm16_to_float32_audio(self, raw_bytes: bytes):
        np = self._np()
        if not raw_bytes:
            return np.asarray([], dtype=np.float32)

        frame_size = max(self._config.sample_width_bytes * self._config.channels, 1)
        aligned_size = len(raw_bytes) - (len(raw_bytes) % frame_size)
        if aligned_size <= 0:
            return np.asarray([], dtype=np.float32)

        if self._config.sample_width_bytes != 2:
            raise RuntimeError("sherpa_onnx_streaming backend는 현재 16-bit PCM 입력만 지원합니다.")

        pcm = np.frombuffer(raw_bytes[:aligned_size], dtype=np.int16).astype(np.float32)
        if self._config.channels > 1:
            pcm = pcm.reshape(-1, self._config.channels).mean(axis=1)
        return np.clip(pcm / 32768.0, -1.0, 1.0)

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
        if not text:
            return ""

        trimmed = text.strip()
        if not trimmed:
            return ""

        significant_text = SherpaOnnxStreamingSpeechToTextService._significant_text(trimmed)
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

    @staticmethod
    def _np():
        import numpy as np

        return np
