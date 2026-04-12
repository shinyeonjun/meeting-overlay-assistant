"""오디오 영역의 basic 서비스를 제공한다."""
from __future__ import annotations

from server.app.services.audio.stt.transcription import SpeechToTextService


def build_placeholder() -> SpeechToTextService:
    """Placeholder STT 서비스를 생성한다."""

    from server.app.services.audio.stt.placeholder_speech_to_text_service import (
        PlaceholderSpeechToTextService,
    )

    return PlaceholderSpeechToTextService()


def build_openai_compatible_audio(
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
    """OpenAI 호환 오디오 전사 서비스를 생성한다."""

    from server.app.services.audio.stt.openai_compatible_audio_transcription_service import (
        OpenAICompatibleAudioTranscriptionService,
    )

    return OpenAICompatibleAudioTranscriptionService(
        model=model_id,
        base_url=base_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
        language=language,
        sample_rate_hz=sample_rate_hz,
        sample_width_bytes=sample_width_bytes,
        channels=channels,
    )
