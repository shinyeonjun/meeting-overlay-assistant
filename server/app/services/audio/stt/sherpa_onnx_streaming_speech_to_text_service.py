"""오디오 영역의 sherpa onnx streaming speech to text service 서비스를 제공한다."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment
from server.app.services.audio.stt.common.preview_stability import normalize_text
from server.app.services.audio.stt.sherpa.audio import (
    duration_ms_to_bytes,
    pcm16_to_float32_audio,
)
from server.app.services.audio.stt.sherpa.artifacts import (
    resolve_transducer_artifacts,
    sort_artifact_matches,
)
from server.app.services.audio.stt.sherpa.preview_results import (
    append_live_final_result,
    append_preview_result,
)
from server.app.services.audio.stt.sherpa.recognizer import create_online_recognizer
from server.app.services.audio.stt.sherpa.state import (
    SherpaStreamingState,
    create_streaming_state,
    reset_streaming_state,
)
from server.app.services.audio.stt.sherpa.streaming_logic import (
    compute_stable_preview,
    is_meaningful_growth,
    merge_with_previous_stable_preview,
)
from server.app.services.audio.stt.transcription import (
    StreamingSpeechToTextService,
    TranscriptionResult,
    record_current_preview_stage,
)


@dataclass(frozen=True)
class SherpaOnnxStreamingConfig:
    """sherpa-onnx streaming 실행 설정."""

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
    """빠른 preview/live_final 생성을 위한 sherpa-onnx 구현."""

    def __init__(self, config: SherpaOnnxStreamingConfig) -> None:
        self._config = config
        self._recognizer = self._create_recognizer(config)
        self._stream = self._recognizer.create_stream()
        self._state = create_streaming_state(
            history_size=max(config.partial_agreement_window, 1)
        )
        self._emit_interval_bytes = duration_ms_to_bytes(
            duration_ms=config.partial_emit_interval_ms,
            sample_rate_hz=config.sample_rate_hz,
            sample_width_bytes=config.sample_width_bytes,
            channels=config.channels,
        )

    def preview_chunk(self, chunk: bytes) -> list[TranscriptionResult]:
        if not chunk:
            return []

        self._stream.accept_waveform(
            self._config.sample_rate_hz,
            self._pcm16_to_float32_audio(chunk),
        )
        self._state.bytes_since_emit += len(chunk)

        while self._recognizer.is_ready(self._stream):
            self._recognizer.decode_stream(self._stream)

        if self._state.bytes_since_emit < self._emit_interval_bytes:
            return []
        self._state.bytes_since_emit = 0

        current_text = self._recognizer.get_result(self._stream).strip()
        normalized_text = normalize_text(current_text)
        if not normalized_text:
            return []
        record_current_preview_stage("sherpa_non_empty")

        preview_results: list[TranscriptionResult] = []
        append_preview_result(
            state=self._state,
            current_text=current_text,
            normalized_text=normalized_text,
            results=preview_results,
        )

        self._state.preview_history.append(normalized_text)
        stable_preview = self._compute_stable_preview(current_text)
        append_live_final_result(
            state=self._state,
            stable_preview=stable_preview,
            results=preview_results,
        )
        return preview_results

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
        reset_streaming_state(self._state)

    @classmethod
    def _create_recognizer(cls, config: SherpaOnnxStreamingConfig):
        return create_online_recognizer(
            config=config,
            resolve_transducer_artifacts=cls._resolve_transducer_artifacts,
        )

    @classmethod
    def _resolve_transducer_artifacts(cls, model_dir: Path) -> dict[str, Path]:
        return resolve_transducer_artifacts(model_dir)

    @staticmethod
    def _sort_artifact_matches(key: str, matches) -> list[Path]:
        return sort_artifact_matches(key, matches)

    def _compute_stable_preview(self, latest_text: str) -> str:
        stable_preview = compute_stable_preview(
            preview_history=list(self._state.preview_history),
            latest_text=latest_text,
            last_stable_preview=self._state.last_stable_preview,
            last_emitted_live_final=self._state.last_emitted_live_final,
            agreement_min_count=self._config.partial_agreement_min_count,
            min_stable_chars=self._config.partial_min_stable_chars,
            min_growth_chars=self._config.partial_min_growth_chars,
            backtrack_tolerance_chars=self._config.partial_backtrack_tolerance_chars,
            commit_min_chars_without_boundary=self._config.partial_commit_min_chars_without_boundary,
        )
        if not stable_preview:
            return ""

        self._state.last_stable_preview = stable_preview
        return stable_preview

    def _merge_with_previous_stable_preview(self, committed_preview: str) -> str:
        return merge_with_previous_stable_preview(
            committed_preview=committed_preview,
            last_stable_preview=self._state.last_stable_preview,
            backtrack_tolerance_chars=self._config.partial_backtrack_tolerance_chars,
        )

    def _is_meaningful_growth(self, stable_preview: str) -> bool:
        return is_meaningful_growth(
            stable_preview=stable_preview,
            last_emitted_live_final=self._state.last_emitted_live_final,
            min_growth_chars=self._config.partial_min_growth_chars,
        )

    def _duration_ms_to_bytes(self, duration_ms: int) -> int:
        return duration_ms_to_bytes(
            duration_ms=duration_ms,
            sample_rate_hz=self._config.sample_rate_hz,
            sample_width_bytes=self._config.sample_width_bytes,
            channels=self._config.channels,
        )

    def _pcm16_to_float32_audio(self, raw_bytes: bytes):
        return pcm16_to_float32_audio(
            raw_bytes=raw_bytes,
            sample_width_bytes=self._config.sample_width_bytes,
            channels=self._config.channels,
            np_module=self._np(),
        )

    @staticmethod
    def _np():
        import numpy as np

        return np

    @property
    def _preview_revision(self) -> int:
        return self._state.preview_revision

    @_preview_revision.setter
    def _preview_revision(self, value: int) -> None:
        self._state.preview_revision = value

    @property
    def _last_preview_text(self) -> str:
        return self._state.last_preview_text

    @_last_preview_text.setter
    def _last_preview_text(self, value: str) -> None:
        self._state.last_preview_text = value

    @property
    def _last_partial_text(self) -> str:
        return self._state.last_partial_text

    @_last_partial_text.setter
    def _last_partial_text(self, value: str) -> None:
        self._state.last_partial_text = value

    @property
    def _last_emitted_live_final(self) -> str:
        return self._state.last_emitted_live_final

    @_last_emitted_live_final.setter
    def _last_emitted_live_final(self, value: str) -> None:
        self._state.last_emitted_live_final = value

    @property
    def _last_emitted_preview(self) -> str:
        return self._state.last_emitted_preview

    @_last_emitted_preview.setter
    def _last_emitted_preview(self, value: str) -> None:
        self._state.last_emitted_preview = value

    @property
    def _last_stable_preview(self) -> str:
        return self._state.last_stable_preview

    @_last_stable_preview.setter
    def _last_stable_preview(self, value: str) -> None:
        self._state.last_stable_preview = value

    @property
    def _bytes_since_emit(self) -> int:
        return self._state.bytes_since_emit

    @_bytes_since_emit.setter
    def _bytes_since_emit(self, value: int) -> None:
        self._state.bytes_since_emit = value

    @property
    def _preview_history(self):
        return self._state.preview_history
