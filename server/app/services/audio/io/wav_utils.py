"""오디오 영역의 wav utils 서비스를 제공한다."""
from __future__ import annotations

from io import BytesIO
import wave


def wrap_pcm16_as_wav(
    raw_bytes: bytes,
    sample_rate_hz: int,
    sample_width_bytes: int,
    channels: int,
) -> bytes:
    """PCM 바이트를 WAV 바이트로 변환한다."""
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width_bytes)
        wav_file.setframerate(sample_rate_hz)
        wav_file.writeframes(raw_bytes)
    return buffer.getvalue()
