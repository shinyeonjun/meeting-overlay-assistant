"""오디오 영역의 audio conversion 서비스를 제공한다."""
from __future__ import annotations

from typing import Any

from .imports import import_numpy


def float32_audio_to_pcm16_bytes(frames: Any) -> bytes:
    """float32 프레임을 16-bit PCM 바이트로 변환한다."""

    np = import_numpy()
    array = np.asarray(frames, dtype=np.float32)
    if array.ndim == 2:
        array = array.mean(axis=1)
    array = np.clip(array, -1.0, 1.0)
    pcm16 = (array * 32767.0).astype(np.int16)
    return pcm16.tobytes()
