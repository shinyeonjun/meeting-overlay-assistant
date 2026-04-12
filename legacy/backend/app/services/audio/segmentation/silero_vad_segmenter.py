"""Silero VAD 2단계 검증 세그먼터."""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.services.audio.segmentation.speech_segmenter import AudioSegmenter, SpeechSegment


@dataclass(frozen=True)
class SileroVadValidatorConfig:
    """Silero VAD 검증 설정."""

    sample_rate_hz: int = 16000
    sample_width_bytes: int = 2
    channels: int = 1
    threshold: float = 0.5
    min_speech_duration_ms: int = 120


class SileroValidatedSpeechSegmenter:
    """기존 세그먼터 결과를 Silero VAD로 2차 검증한다."""

    def __init__(self, base_segmenter: AudioSegmenter, config: SileroVadValidatorConfig) -> None:
        self._base_segmenter = base_segmenter
        self._config = config
        self._model = None

    def split(self, chunk: bytes) -> list[SpeechSegment]:
        segments = self._base_segmenter.split(chunk)
        if not segments:
            return []

        return [segment for segment in segments if self._is_speech(segment)]

    def _is_speech(self, segment: SpeechSegment) -> bool:
        speech_timestamps = self._get_speech_timestamps(segment.raw_bytes)
        if not speech_timestamps:
            return False

        minimum_samples = int(
            self._config.sample_rate_hz * (self._config.min_speech_duration_ms / 1000.0)
        )
        for timestamp in speech_timestamps:
            start = int(timestamp.get("start", 0))
            end = int(timestamp.get("end", 0))
            if end - start >= minimum_samples:
                return True
        return False

    def _get_speech_timestamps(self, raw_bytes: bytes) -> list[dict[str, int]]:
        np = self._np()
        audio = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        if self._config.channels > 1:
            audio = audio.reshape(-1, self._config.channels).mean(axis=1)
        if audio.size == 0:
            return []

        get_speech_timestamps, _save_audio, _read_audio, _vad_iterator, collect_chunks = (
            self._load_silero_components()
        )
        return get_speech_timestamps(
            audio,
            self._get_model(),
            threshold=self._config.threshold,
            sampling_rate=self._config.sample_rate_hz,
        )

    def _get_model(self):
        if self._model is None:
            _get_speech_timestamps, _save_audio, _read_audio, _vad_iterator, collect_chunks = (
                self._load_silero_components()
            )
            self._model = self._load_silero_model()
        return self._model

    @staticmethod
    def _load_silero_components():
        try:
            from silero_vad import collect_chunks, get_speech_timestamps, read_audio, save_audio, VADIterator
        except ImportError as error:
            raise RuntimeError(
                "Silero VAD를 사용하려면 silero-vad 패키지를 설치해야 합니다."
            ) from error
        return get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks

    @staticmethod
    def _load_silero_model():
        try:
            from silero_vad import load_silero_vad
        except ImportError as error:
            raise RuntimeError(
                "Silero VAD를 사용하려면 silero-vad 패키지를 설치해야 합니다."
            ) from error
        return load_silero_vad()

    @staticmethod
    def _np():
        import numpy as np

        return np

