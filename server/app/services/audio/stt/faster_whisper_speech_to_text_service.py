"""faster-whisper 기반 STT 구현체."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Any

from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment
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

    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        audio = self._pcm16_to_float32_audio(segment.raw_bytes)
        if audio.size == 0:
            return TranscriptionResult(text="", confidence=0.0)

        audio_rms = self._compute_rms(audio)
        if audio_rms < self._config.silence_rms_threshold:
            return TranscriptionResult(text="", confidence=0.0)

        transcribe_kwargs: dict[str, Any] = {
            "language": self._config.language,
            "beam_size": self._config.beam_size,
            "vad_filter": False,
        }
        if self._config.initial_prompt:
            transcribe_kwargs["initial_prompt"] = self._config.initial_prompt

        segments, _info = self._get_model().transcribe(
            audio,
            **transcribe_kwargs,
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

    def _get_model(self, model_name_or_path: str | None = None):
        if self._model is None:
            model_name_or_path = model_name_or_path or self._resolve_model_name_or_path()
            cache_key = (
                model_name_or_path,
                self._config.device,
                self._config.compute_type,
                self._config.cpu_threads,
            )
            with self._MODEL_CACHE_LOCK:
                cached_model = self._MODEL_CACHE.get(cache_key)
                if cached_model is None:
                    model_kwargs: dict[str, Any] = {
                        "device": self._config.device,
                        "compute_type": self._config.compute_type,
                    }
                    if self._config.cpu_threads > 0:
                        model_kwargs["cpu_threads"] = self._config.cpu_threads

                    started_at = perf_counter()
                    logger.info(
                        "faster-whisper 모델 로드 시작: model=%s source=%s device=%s compute_type=%s",
                        self._config.model_id,
                        model_name_or_path,
                        self._config.device,
                        self._config.compute_type,
                    )
                    cached_model = self._load_model_class()(model_name_or_path, **model_kwargs)
                    setattr(cached_model, "_caps_model_source", model_name_or_path)
                    self._MODEL_CACHE[cache_key] = cached_model
                    logger.info(
                        "faster-whisper 모델 로드 완료: model=%s source=%s elapsed=%.3fs",
                        self._config.model_id,
                        model_name_or_path,
                        perf_counter() - started_at,
                    )
                else:
                    logger.debug(
                        "faster-whisper 모델 캐시 재사용: model=%s source=%s",
                        self._config.model_id,
                        model_name_or_path,
                    )
                self._model = cached_model
        return self._model

    def _resolve_model_name_or_path(self, *, local_only: bool = False) -> str | None:
        explicit_model_path = self._resolve_explicit_model_path()
        if explicit_model_path is not None:
            return str(explicit_model_path)

        local_model_path = self._resolve_cached_model_path()
        if local_model_path is not None:
            return str(local_model_path)

        if local_only:
            return None

        logger.warning(
            "faster-whisper 로컬 캐시를 찾지 못해 model_id로 직접 로드합니다: model=%s",
            self._config.model_id,
        )
        return self._config.model_id

    def _resolve_explicit_model_path(self) -> Path | None:
        if self._config.model_path is None:
            return None

        path = self._config.model_path.resolve()
        if self._is_valid_model_directory(path):
            return path

        logger.warning(
            "faster-whisper model_path가 유효하지 않아 무시합니다: model=%s path=%s",
            self._config.model_id,
            path,
        )
        return None

    def _resolve_cached_model_path(self) -> Path | None:
        try:
            from faster_whisper.utils import download_model
        except ImportError:
            return None

        try:
            resolved_path = download_model(
                self._config.model_id,
                local_files_only=True,
            )
        except Exception:
            return None

        path = Path(resolved_path).resolve()
        if not self._is_valid_model_directory(path):
            return None

        logger.debug(
            "faster-whisper 로컬 캐시 경로 사용: model=%s path=%s",
            self._config.model_id,
            path,
        )
        return path

    @staticmethod
    def _is_valid_model_directory(path: Path) -> bool:
        required_files = (
            "model.bin",
            "config.json",
            "tokenizer.json",
            "vocabulary.json",
        )
        return path.exists() and path.is_dir() and all((path / filename).exists() for filename in required_files)

    def _pcm16_to_float32_audio(self, raw_bytes: bytes):
        np = self._np()
        if not raw_bytes:
            return np.asarray([], dtype=np.float32)

        frame_size = max(self._config.sample_width_bytes * self._config.channels, 1)
        aligned_size = len(raw_bytes) - (len(raw_bytes) % frame_size)
        if aligned_size <= 0:
            return np.asarray([], dtype=np.float32)

        if self._config.sample_width_bytes != 2:
            raise RuntimeError("faster_whisper backend는 현재 16-bit PCM 입력만 지원합니다.")

        pcm = np.frombuffer(raw_bytes[:aligned_size], dtype=np.int16).astype(np.float32)
        if self._config.channels > 1:
            pcm = pcm.reshape(-1, self._config.channels).mean(axis=1)
        return np.clip(pcm / 32768.0, -1.0, 1.0)

    def _average_confidence(self, segments: list[Any], text: str) -> float:
        avg_logprobs = [
            float(segment.avg_logprob)
            for segment in segments
            if getattr(segment, "avg_logprob", None) is not None
        ]
        if not avg_logprobs:
            return 0.8 if text else 0.0
        probabilities = [min(max(math.exp(value), 0.0), 1.0) for value in avg_logprobs]
        return round(sum(probabilities) / len(probabilities), 4)

    def _max_no_speech_prob(self, segments: list[Any]) -> float | None:
        probabilities = [
            float(segment.no_speech_prob)
            for segment in segments
            if getattr(segment, "no_speech_prob", None) is not None
        ]
        if not probabilities:
            return None
        return round(max(probabilities), 4)

    def _compute_rms(self, audio) -> float:
        np = self._np()
        if audio.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(np.square(audio, dtype=np.float32))))

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

