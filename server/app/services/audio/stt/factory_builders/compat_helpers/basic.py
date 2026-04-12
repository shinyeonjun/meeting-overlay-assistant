"""기본 STT compat wrapper."""

from __future__ import annotations

from server.app.services.audio.stt.factory_builders import (
    build_openai_compatible_audio,
    build_placeholder,
)
from server.app.services.audio.stt.transcription import SpeechToTextService


def build_placeholder_compat() -> SpeechToTextService:
    """기존 placeholder builder 호환 wrapper."""

    return build_placeholder()


def build_openai_compatible_audio_compat(
    *,
    model_id: str,
    base_url: str,
    api_key: str | None,
    timeout_seconds: float,
    language: str | None,
    sample_rate_hz: int,
    sample_width_bytes: int,
    channels: int,
) -> SpeechToTextService:
    """기존 OpenAI compatible audio builder 호환 wrapper."""

    return build_openai_compatible_audio(
        model_id=model_id,
        base_url=base_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
        language=language,
        sample_rate_hz=sample_rate_hz,
        sample_width_bytes=sample_width_bytes,
        channels=channels,
    )
