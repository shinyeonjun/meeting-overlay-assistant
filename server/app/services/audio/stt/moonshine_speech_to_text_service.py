"""Moonshine 기반 STT 구현체."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment
from server.app.services.audio.stt.moonshine.audio import (
    compute_rms,
    pcm16_to_float32_audio,
)
from server.app.services.audio.stt.moonshine.backend import (
    cleanup_temp_wave,
    infer_language_code,
    infer_model_arch_from_name,
    load_wave_for_moonshine_voice,
    resolve_model_name,
    resolve_moonshine_voice_model,
    run_transcribe,
    run_transcribe_with_moonshine_voice,
    write_segment_to_temp_wave,
)
from server.app.services.audio.stt.transcription import SpeechToTextService, TranscriptionResult


@dataclass(frozen=True)
class MoonshineConfig:
    """Moonshine 실행 설정."""

    model_id: str
    model_path: Path | None = None
    language: str | None = "ko"
    sample_rate_hz: int = 16000
    sample_width_bytes: int = 2
    channels: int = 1
    silence_rms_threshold: float = 0.003


class MoonshineSpeechToTextService(SpeechToTextService):
    """Moonshine으로 발화 구간을 전사한다."""

    def __init__(self, config: MoonshineConfig) -> None:
        self._config = config

    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        audio = self._pcm16_to_float32_audio(segment.raw_bytes)
        if audio.size == 0:
            return TranscriptionResult(text="", confidence=0.0)

        if self._compute_rms(audio) < self._config.silence_rms_threshold:
            return TranscriptionResult(text="", confidence=0.0)

        wav_path = self._write_segment_to_temp_wave(segment.raw_bytes)
        try:
            texts = self._run_transcribe(
                audio_paths=[wav_path],
                model_name=self._resolve_model_name(),
            )
        finally:
            cleanup_temp_wave(wav_path)

        text = " ".join(item.strip() for item in texts if item and item.strip()).strip()
        return TranscriptionResult(text=text, confidence=0.8 if text else 0.0)

    def _resolve_model_name(self) -> str:
        return resolve_model_name(
            model_id=self._config.model_id,
            model_path=self._config.model_path,
        )

    def _write_segment_to_temp_wave(self, raw_bytes: bytes) -> str:
        return write_segment_to_temp_wave(
            raw_bytes=raw_bytes,
            channels=self._config.channels,
            sample_width_bytes=self._config.sample_width_bytes,
            sample_rate_hz=self._config.sample_rate_hz,
        )

    def _pcm16_to_float32_audio(self, raw_bytes: bytes):
        return pcm16_to_float32_audio(
            raw_bytes=raw_bytes,
            sample_width_bytes=self._config.sample_width_bytes,
            channels=self._config.channels,
            np_module=self._np(),
        )

    def _compute_rms(self, audio) -> float:
        return compute_rms(audio, np_module=self._np())

    @staticmethod
    def _run_transcribe(*, audio_paths: list[str], model_name: str) -> list[str]:
        return run_transcribe(audio_paths=audio_paths, model_name=model_name)

    @staticmethod
    def _run_transcribe_with_moonshine_voice(
        *,
        audio_paths: list[str],
        model_name: str,
    ) -> list[str]:
        return run_transcribe_with_moonshine_voice(
            audio_paths=audio_paths,
            model_name=model_name,
        )

    @staticmethod
    def _resolve_moonshine_voice_model(
        *,
        model_name: str,
        get_model_for_language,
        string_to_model_arch,
        model_arch_enum,
    ) -> tuple[str, object]:
        return resolve_moonshine_voice_model(
            model_name=model_name,
            get_model_for_language=get_model_for_language,
            string_to_model_arch=string_to_model_arch,
            model_arch_enum=model_arch_enum,
        )

    @staticmethod
    def _infer_language_code(model_name: str) -> str:
        return infer_language_code(model_name)

    @staticmethod
    def _infer_model_arch_from_name(
        model_name: str,
        *,
        string_to_model_arch,
        model_arch_enum,
    ):
        return infer_model_arch_from_name(
            model_name,
            string_to_model_arch=string_to_model_arch,
            model_arch_enum=model_arch_enum,
        )

    @staticmethod
    def _load_wave_for_moonshine_voice(audio_path: str) -> tuple[list[float], int]:
        return load_wave_for_moonshine_voice(audio_path)

    @staticmethod
    def _np():
        import numpy as np

        return np
