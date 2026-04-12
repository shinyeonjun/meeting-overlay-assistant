"""오디오 영역의 local 서비스를 제공한다."""
from __future__ import annotations

from pathlib import Path

from server.app.services.audio.stt.transcription import SpeechToTextService


def build_amd_whisper_npu(
    *,
    model_id: str,
    model_path: str | None,
    base_model_id: str | None,
    installation_path: str | None,
    encoder_model_path: str | None,
    decoder_model_path: str | None,
    encoder_rai_path: str | None,
    language: str | None,
    sample_rate_hz: int,
    sample_width_bytes: int,
    channels: int,
    silence_rms_threshold: float,
) -> SpeechToTextService:
    """AMD Whisper NPU 서비스를 생성한다."""

    from server.app.services.audio.stt.amd_whisper_npu_speech_to_text_service import (
        AMDWhisperNPUConfig,
        AMDWhisperNPUSpeechToTextService,
    )

    return AMDWhisperNPUSpeechToTextService(
        config=AMDWhisperNPUConfig(
            model_id=model_id,
            model_path=Path(model_path).resolve() if model_path else None,
            base_model_id=base_model_id,
            installation_path=Path(installation_path).resolve() if installation_path else None,
            encoder_model_path=Path(encoder_model_path).resolve() if encoder_model_path else None,
            decoder_model_path=Path(decoder_model_path).resolve() if decoder_model_path else None,
            encoder_rai_path=Path(encoder_rai_path).resolve() if encoder_rai_path else None,
            language=language,
            sample_rate_hz=sample_rate_hz,
            sample_width_bytes=sample_width_bytes,
            channels=channels,
            silence_rms_threshold=silence_rms_threshold,
        )
    )


def build_faster_whisper(
    *,
    model_id: str,
    model_path: str | None,
    language: str | None,
    initial_prompt: str | None,
    device: str,
    compute_type: str,
    cpu_threads: int,
    beam_size: int,
    sample_rate_hz: int,
    sample_width_bytes: int,
    channels: int,
    silence_rms_threshold: float,
) -> SpeechToTextService:
    """Faster Whisper 비스트리밍 서비스를 생성한다."""

    from server.app.services.audio.stt.faster_whisper_speech_to_text_service import (
        FasterWhisperConfig,
        FasterWhisperSpeechToTextService,
    )

    return FasterWhisperSpeechToTextService(
        config=FasterWhisperConfig(
            model_id=model_id,
            model_path=Path(model_path).resolve() if model_path else None,
            language=language,
            initial_prompt=initial_prompt,
            device=device,
            compute_type=compute_type,
            cpu_threads=cpu_threads,
            beam_size=beam_size,
            sample_rate_hz=sample_rate_hz,
            sample_width_bytes=sample_width_bytes,
            channels=channels,
            silence_rms_threshold=silence_rms_threshold,
        )
    )


def build_moonshine(
    *,
    model_id: str,
    model_path: str | None,
    language: str | None,
    sample_rate_hz: int,
    sample_width_bytes: int,
    channels: int,
    silence_rms_threshold: float,
) -> SpeechToTextService:
    """Moonshine 비스트리밍 서비스를 생성한다."""

    from server.app.services.audio.stt.moonshine_speech_to_text_service import (
        MoonshineConfig,
        MoonshineSpeechToTextService,
    )

    return MoonshineSpeechToTextService(
        config=MoonshineConfig(
            model_id=model_id,
            model_path=Path(model_path).resolve() if model_path else None,
            language=language,
            sample_rate_hz=sample_rate_hz,
            sample_width_bytes=sample_width_bytes,
            channels=channels,
            silence_rms_threshold=silence_rms_threshold,
        )
    )
