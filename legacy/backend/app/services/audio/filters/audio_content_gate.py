"""STT 이전 단계에서 비음성/음악 세그먼트를 거르는 게이트."""

from __future__ import annotations

import math
from dataclasses import dataclass

from backend.app.services.audio.segmentation.speech_segmenter import SpeechSegment


@dataclass(frozen=True)
class AudioContentGateProfile:
    """오디오 content gate 판정 기준."""

    enabled: bool
    sample_rate_hz: int
    sample_width_bytes: int
    channels: int
    min_rms: float
    min_speech_band_ratio: float
    min_spectral_flatness: float
    min_zero_crossing_rate: float


class AudioContentGate:
    """세그먼트가 STT에 올릴 만한 음성인지 빠르게 판별한다."""

    def __init__(self, profile: AudioContentGateProfile) -> None:
        self._profile = profile

    def should_process(self, segment: SpeechSegment) -> bool:
        """세그먼트를 STT로 넘길지 판단한다."""
        if not self._profile.enabled:
            return True

        samples = self._load_samples(segment.raw_bytes)
        if samples.size == 0:
            return False

        rms = float(self._numpy.sqrt(self._numpy.mean(self._numpy.square(samples))))
        if rms < self._profile.min_rms:
            return False

        spectral_flatness = self._calculate_spectral_flatness(samples)
        if spectral_flatness < self._profile.min_spectral_flatness:
            return False

        zero_crossing_rate = self._calculate_zero_crossing_rate(samples)
        if zero_crossing_rate < self._profile.min_zero_crossing_rate:
            return False

        speech_band_ratio = self._calculate_speech_band_ratio(samples)
        if speech_band_ratio < self._profile.min_speech_band_ratio:
            return False

        return True

    @property
    def _numpy(self):
        import numpy as np

        return np

    def _load_samples(self, raw_bytes: bytes):
        np = self._numpy
        if self._profile.sample_width_bytes != 2:
            raise ValueError("AudioContentGate는 현재 16-bit PCM만 지원합니다.")

        samples = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        if self._profile.channels > 1:
            samples = samples.reshape(-1, self._profile.channels).mean(axis=1)
        return samples

    def _calculate_zero_crossing_rate(self, samples) -> float:
        np = self._numpy
        if samples.size < 2:
            return 0.0
        zero_crossings = np.count_nonzero(np.diff(np.signbit(samples)))
        return float(zero_crossings / max(samples.size - 1, 1))

    def _calculate_spectral_flatness(self, samples) -> float:
        np = self._numpy
        magnitude = np.abs(np.fft.rfft(samples))
        magnitude = np.maximum(magnitude, 1e-12)
        geometric_mean = math.exp(float(np.mean(np.log(magnitude))))
        arithmetic_mean = float(np.mean(magnitude))
        if arithmetic_mean <= 0:
            return 0.0
        return geometric_mean / arithmetic_mean

    def _calculate_speech_band_ratio(self, samples) -> float:
        np = self._numpy
        spectrum = np.abs(np.fft.rfft(samples))
        frequencies = np.fft.rfftfreq(samples.size, d=1 / self._profile.sample_rate_hz)
        total_energy = float(np.sum(spectrum))
        if total_energy <= 0:
            return 0.0
        speech_band = spectrum[(frequencies >= 250) & (frequencies <= 3800)]
        return float(np.sum(speech_band) / total_energy)

