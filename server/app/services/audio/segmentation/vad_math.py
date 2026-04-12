"""오디오 영역의 vad math 서비스를 제공한다."""
from __future__ import annotations

from time import time


def now_ms() -> int:
    """현재 시간을 밀리초로 반환한다."""

    return int(time() * 1000)


def classify_frame(config, noise_floor_rms: float, rms: float, *, active: bool) -> bool:
    """현재 frame이 voiced인지 분류한다."""

    threshold = max(
        config.rms_threshold,
        noise_floor_rms * config.adaptive_threshold_multiplier,
    )
    if active:
        threshold *= config.active_threshold_ratio
    return rms >= threshold


def update_noise_floor(config, noise_floor_rms: float, rms: float) -> float:
    """적응형 noise floor를 업데이트한다."""

    alpha = config.adaptive_noise_floor_alpha
    return (alpha * noise_floor_rms) + ((1 - alpha) * rms)


def calculate_rms(config, frame_bytes: bytes) -> float:
    """PCM frame의 RMS 값을 계산한다."""

    np = import_numpy()

    if config.sample_width_bytes != 2:
        raise ValueError("현재 VAD 세그먼터는 16-bit PCM만 지원합니다.")

    samples = np.frombuffer(frame_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    if config.channels > 1:
        samples = samples.reshape(-1, config.channels).mean(axis=1)
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(samples))))


def import_numpy():
    """numpy를 지연 import한다."""

    import numpy as np

    return np
