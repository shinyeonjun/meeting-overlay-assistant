"""오디오 영역의 local 서비스를 제공한다."""
from __future__ import annotations

from server.app.services.audio.stt.factory_builders import (
    build_amd_whisper_npu,
    build_faster_whisper,
    build_moonshine,
)
from server.app.services.audio.stt.transcription import SpeechToTextService


def build_amd_whisper_npu_compat(
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
    """기존 AMD Whisper NPU builder 호환 wrapper."""

    return build_amd_whisper_npu(
        model_id=model_id,
        model_path=model_path,
        base_model_id=base_model_id,
        installation_path=installation_path,
        encoder_model_path=encoder_model_path,
        decoder_model_path=decoder_model_path,
        encoder_rai_path=encoder_rai_path,
        language=language,
        sample_rate_hz=sample_rate_hz,
        sample_width_bytes=sample_width_bytes,
        channels=channels,
        silence_rms_threshold=silence_rms_threshold,
    )


def build_faster_whisper_compat(
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
    """기존 Faster Whisper builder 호환 wrapper."""

    return build_faster_whisper(
        model_id=model_id,
        model_path=model_path,
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


def build_moonshine_compat(
    *,
    model_id: str,
    model_path: str | None,
    language: str | None,
    sample_rate_hz: int,
    sample_width_bytes: int,
    channels: int,
    silence_rms_threshold: float,
) -> SpeechToTextService:
    """기존 Moonshine builder 호환 wrapper."""

    return build_moonshine(
        model_id=model_id,
        model_path=model_path,
        language=language,
        sample_rate_hz=sample_rate_hz,
        sample_width_bytes=sample_width_bytes,
        channels=channels,
        silence_rms_threshold=silence_rms_threshold,
    )
