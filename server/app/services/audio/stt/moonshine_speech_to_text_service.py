"""Moonshine 기반 STT 구현체."""

from __future__ import annotations

import os
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment
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
            try:
                os.remove(wav_path)
            except OSError:
                pass

        text = " ".join(item.strip() for item in texts if item and item.strip()).strip()
        return TranscriptionResult(text=text, confidence=0.8 if text else 0.0)

    def _resolve_model_name(self) -> str:
        return str(self._config.model_path) if self._config.model_path else self._config.model_id

    def _write_segment_to_temp_wave(self, raw_bytes: bytes) -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = temp_file.name

        with wave.open(temp_path, "wb") as wav_file:
            wav_file.setnchannels(self._config.channels)
            wav_file.setsampwidth(self._config.sample_width_bytes)
            wav_file.setframerate(self._config.sample_rate_hz)
            wav_file.writeframes(raw_bytes)

        return temp_path

    def _pcm16_to_float32_audio(self, raw_bytes: bytes):
        np = self._np()
        if not raw_bytes:
            return np.asarray([], dtype=np.float32)

        frame_size = max(self._config.sample_width_bytes * self._config.channels, 1)
        aligned_size = len(raw_bytes) - (len(raw_bytes) % frame_size)
        if aligned_size <= 0:
            return np.asarray([], dtype=np.float32)

        if self._config.sample_width_bytes != 2:
            raise RuntimeError("moonshine backend는 현재 16-bit PCM 입력만 지원합니다.")

        pcm = np.frombuffer(raw_bytes[:aligned_size], dtype=np.int16).astype(np.float32)
        if self._config.channels > 1:
            pcm = pcm.reshape(-1, self._config.channels).mean(axis=1)
        return np.clip(pcm / 32768.0, -1.0, 1.0)

    def _compute_rms(self, audio) -> float:
        np = self._np()
        if audio.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(np.square(audio, dtype=np.float32))))

    @staticmethod
    def _run_transcribe(*, audio_paths: list[str], model_name: str) -> list[str]:
        try:
            from moonshine_onnx import transcribe
        except ImportError:
            return MoonshineSpeechToTextService._run_transcribe_with_moonshine_voice(
                audio_paths=audio_paths,
                model_name=model_name,
            )

        results = transcribe(audio=audio_paths, model_name=model_name)
        return [str(item) for item in results]

    @staticmethod
    def _run_transcribe_with_moonshine_voice(
        *,
        audio_paths: list[str],
        model_name: str,
    ) -> list[str]:
        try:
            from moonshine_voice import Transcriber, get_model_for_language
            from moonshine_voice.moonshine_api import ModelArch, string_to_model_arch
        except ImportError as error:
            raise RuntimeError(
                "moonshine backend를 사용하려면 moonshine_onnx 또는 moonshine_voice 패키지를 설치해야 합니다."
            ) from error

        model_path, model_arch = MoonshineSpeechToTextService._resolve_moonshine_voice_model(
            model_name=model_name,
            get_model_for_language=get_model_for_language,
            string_to_model_arch=string_to_model_arch,
            model_arch_enum=ModelArch,
        )

        texts: list[str] = []
        with Transcriber(model_path=model_path, model_arch=model_arch) as transcriber:
            for audio_path in audio_paths:
                audio, sample_rate = MoonshineSpeechToTextService._load_wave_for_moonshine_voice(audio_path)
                transcript = transcriber.transcribe_without_streaming(
                    audio_data=audio,
                    sample_rate=sample_rate,
                )
                joined = " ".join(
                    line.text.strip()
                    for line in transcript.lines
                    if line.text and line.text.strip()
                ).strip()
                texts.append(joined)
        return texts

    @staticmethod
    def _resolve_moonshine_voice_model(
        *,
        model_name: str,
        get_model_for_language,
        string_to_model_arch,
        model_arch_enum,
    ) -> tuple[str, object]:
        candidate_path = Path(model_name)
        if candidate_path.exists():
            inferred_arch = MoonshineSpeechToTextService._infer_model_arch_from_name(
                candidate_path.name,
                string_to_model_arch=string_to_model_arch,
                model_arch_enum=model_arch_enum,
            )
            return str(candidate_path), inferred_arch

        normalized = model_name.split("/")[-1].strip().casefold()
        language = MoonshineSpeechToTextService._infer_language_code(normalized)
        wanted_arch = MoonshineSpeechToTextService._infer_model_arch_from_name(
            normalized,
            string_to_model_arch=string_to_model_arch,
            model_arch_enum=model_arch_enum,
        )
        return get_model_for_language(wanted_language=language, wanted_model_arch=wanted_arch)

    @staticmethod
    def _infer_language_code(model_name: str) -> str:
        for language in ("ko", "ja", "en", "es", "ar", "vi", "uk", "zh"):
            if model_name.endswith(f"-{language}") or f"-{language}-" in model_name:
                return language
        return "ko"

    @staticmethod
    def _infer_model_arch_from_name(
        model_name: str,
        *,
        string_to_model_arch,
        model_arch_enum,
    ):
        name = model_name.casefold()
        candidates = (
            "medium-streaming",
            "small-streaming",
            "base-streaming",
            "tiny-streaming",
            "base",
            "tiny",
        )
        for candidate in candidates:
            if candidate in name:
                return string_to_model_arch(candidate)
        return model_arch_enum.TINY

    @staticmethod
    def _load_wave_for_moonshine_voice(audio_path: str) -> tuple[list[float], int]:
        with wave.open(audio_path, "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            frame_count = wav_file.getnframes()
            raw_bytes = wav_file.readframes(frame_count)

        if sample_width != 2:
            raise RuntimeError("moonshine_voice backend는 현재 16-bit PCM WAV 입력만 지원합니다.")

        np = MoonshineSpeechToTextService._np()
        pcm = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)
        if channels > 1:
            pcm = pcm.reshape(-1, channels).mean(axis=1)
        audio = np.clip(pcm / 32768.0, -1.0, 1.0)
        return audio.tolist(), sample_rate

    @staticmethod
    def _np():
        import numpy as np

        return np

