"""faster-whisper 기반 STT 구현체."""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Any

from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment
from server.app.services.audio.stt.faster_whisper.audio import (
    compute_rms,
    pcm16_to_float32_audio,
)
from server.app.services.audio.stt.faster_whisper.confidence import (
    average_confidence,
    max_no_speech_prob,
)
from server.app.services.audio.stt.faster_whisper.model_runtime import (
    is_valid_model_directory,
    load_cached_model,
    resolve_cached_model_path,
    resolve_explicit_model_path,
    resolve_model_name_or_path,
)
from server.app.services.audio.stt.transcription import SpeechToTextService, TranscriptionResult


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FasterWhisperConfig:
    """faster-whisper 실행 설정."""

    model_id: str
    model_path: Path | None = None
    language: str | None = "ko"
    initial_prompt: str | None = None
    device: str = "auto"
    compute_type: str = "default"
    cpu_threads: int = 0
    beam_size: int = 1
    sample_rate_hz: int = 16000
    sample_width_bytes: int = 2
    channels: int = 1
    silence_rms_threshold: float = 0.003
    vad_filter: bool = False
    vad_min_silence_duration_ms: int | None = None
    vad_speech_pad_ms: int | None = None
    no_speech_threshold: float | None = None
    condition_on_previous_text: bool = True


class FasterWhisperSpeechToTextService(SpeechToTextService):
    """faster-whisper로 발화 구간을 전사한다."""

    _MODEL_CACHE: dict[tuple[str, str, str, int], Any] = {}
    _MODEL_CACHE_LOCK = Lock()

    def __init__(self, config: FasterWhisperConfig) -> None:
        self._config = config
        self._model: Any | None = None

    def preload(self) -> None:
        """모델을 미리 로드해 첫 전사 지연을 줄인다."""

        model_name_or_path = self._resolve_model_name_or_path(local_only=True)
        if model_name_or_path is None:
            logger.warning(
                "faster-whisper preload 생략: 로컬 모델 아티팩트가 아직 준비되지 않았습니다. model=%s",
                self._config.model_id,
            )
            return

        started_at = perf_counter()
        model = self._get_model(model_name_or_path=model_name_or_path)
        elapsed = perf_counter() - started_at
        logger.info(
            "faster-whisper preload 완료: model=%s source=%s elapsed=%.3fs",
            self._config.model_id,
            getattr(model, "_caps_model_source", "unknown"),
            elapsed,
        )
        self._warmup_decode()

    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        audio = self._pcm16_to_float32_audio(segment.raw_bytes)
        if audio.size == 0:
            return TranscriptionResult(text="", confidence=0.0)

        audio_rms = self._compute_rms(audio)
        if audio_rms < self._config.silence_rms_threshold:
            return TranscriptionResult(text="", confidence=0.0)

        model = self._get_model()
        transcribe_kwargs = self._build_transcribe_kwargs()
        segments, _info = model.transcribe(
            audio,
            **self._filter_supported_transcribe_kwargs(model, transcribe_kwargs),
        )
        collected_segments = list(segments)
        text = " ".join(
            item.text.strip()
            for item in collected_segments
            if getattr(item, "text", "").strip()
        ).strip()
        confidence = self._average_confidence(collected_segments, text)
        no_speech_prob = self._max_no_speech_prob(collected_segments)
        return TranscriptionResult(
            text=text,
            confidence=confidence,
            no_speech_prob=no_speech_prob,
        )

    def _build_transcribe_kwargs(self) -> dict[str, Any]:
        transcribe_kwargs: dict[str, Any] = {
            "language": self._config.language,
            "beam_size": self._config.beam_size,
            "vad_filter": self._config.vad_filter,
        }
        if self._config.initial_prompt:
            transcribe_kwargs["initial_prompt"] = self._config.initial_prompt
        if self._config.no_speech_threshold is not None:
            transcribe_kwargs["no_speech_threshold"] = self._config.no_speech_threshold
        if not self._config.condition_on_previous_text:
            transcribe_kwargs["condition_on_previous_text"] = False
        if self._config.vad_filter:
            vad_parameters: dict[str, Any] = {}
            if self._config.vad_min_silence_duration_ms is not None:
                vad_parameters["min_silence_duration_ms"] = (
                    self._config.vad_min_silence_duration_ms
                )
            if self._config.vad_speech_pad_ms is not None:
                vad_parameters["speech_pad_ms"] = self._config.vad_speech_pad_ms
            if vad_parameters:
                transcribe_kwargs["vad_parameters"] = vad_parameters
        return transcribe_kwargs

    def _get_model(self, model_name_or_path: str | None = None):
        if self._model is None:
            model_name_or_path = model_name_or_path or self._resolve_model_name_or_path()
            self._model = load_cached_model(
                config=self._config,
                model_name_or_path=model_name_or_path,
                model_cache=self._MODEL_CACHE,
                model_cache_lock=self._MODEL_CACHE_LOCK,
                load_model_class=self._load_model_class,
                logger=logger,
            )
        return self._model

    def _resolve_model_name_or_path(self, *, local_only: bool = False) -> str | None:
        return resolve_model_name_or_path(
            model_id=self._config.model_id,
            explicit_model_path=self._resolve_explicit_model_path(),
            cached_model_path=self._resolve_cached_model_path(),
            local_only=local_only,
            logger=logger,
        )

    def _resolve_explicit_model_path(self) -> Path | None:
        return resolve_explicit_model_path(
            model_path=self._config.model_path,
            model_id=self._config.model_id,
            logger=logger,
        )

    def _resolve_cached_model_path(self) -> Path | None:
        return resolve_cached_model_path(
            model_id=self._config.model_id,
            logger=logger,
        )

    @staticmethod
    def _is_valid_model_directory(path: Path) -> bool:
        return is_valid_model_directory(path)

    def _pcm16_to_float32_audio(self, raw_bytes: bytes):
        return pcm16_to_float32_audio(
            raw_bytes=raw_bytes,
            sample_width_bytes=self._config.sample_width_bytes,
            channels=self._config.channels,
            np_module=self._np(),
        )

    def _average_confidence(self, segments: list[Any], text: str) -> float:
        return average_confidence(segments=segments, text=text)

    def _max_no_speech_prob(self, segments: list[Any]) -> float | None:
        return max_no_speech_prob(segments=segments)

    def _compute_rms(self, audio) -> float:
        return compute_rms(audio, np_module=self._np())

    @staticmethod
    def _filter_supported_transcribe_kwargs(model, transcribe_kwargs: dict[str, Any]) -> dict[str, Any]:
        """설치된 faster-whisper 버전이 지원하는 인자만 전달한다."""

        try:
            signature = inspect.signature(model.transcribe)
        except (TypeError, ValueError):
            return transcribe_kwargs
        supported_keys = set(signature.parameters)
        return {
            key: value
            for key, value in transcribe_kwargs.items()
            if key in supported_keys
        }

    @staticmethod
    def _load_model_class():
        try:
            from faster_whisper import WhisperModel
        except ImportError as error:
            raise RuntimeError(
                "faster_whisper backend를 사용하려면 faster-whisper 패키지를 설치해야 합니다."
            ) from error
        return WhisperModel

    @classmethod
    def clear_model_cache(cls) -> None:
        """테스트를 위해 프로세스 전역 모델 캐시를 비운다."""

        with cls._MODEL_CACHE_LOCK:
            cls._MODEL_CACHE.clear()

    @staticmethod
    def _np():
        import numpy as np

        return np

    def _warmup_decode(self) -> None:
        """첫 실제 전사 전에 짧은 더미 decode를 수행해 cold-start tail을 줄인다."""

        started_at = perf_counter()
        try:
            self.transcribe(self._build_warmup_segment())
        except Exception:
            logger.warning(
                "faster-whisper warm-up decode 실패: model=%s",
                self._config.model_id,
                exc_info=True,
            )
            return
        logger.info(
            "faster-whisper warm-up decode 완료: model=%s elapsed=%.3fs",
            self._config.model_id,
            perf_counter() - started_at,
        )

    def _build_warmup_segment(self) -> SpeechSegment:
        """무음 필터를 통과하는 짧은 예열용 세그먼트를 만든다."""

        np_module = self._np()
        warmup_samples = np_module.tile(
            np_module.asarray([0, 6000, -6000, 3000], dtype=np_module.int16),
            2000,
        )
        return SpeechSegment(
            start_ms=0,
            end_ms=500,
            raw_bytes=warmup_samples.tobytes(),
        )
