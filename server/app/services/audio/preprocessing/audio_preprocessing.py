"""오디오 영역의 audio preprocessing 서비스를 제공한다."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AudioBuffer:
    """PCM 오디오 버퍼와 메타데이터."""

    sample_rate_hz: int
    sample_width_bytes: int
    channels: int
    raw_bytes: bytes

    @property
    def bytes_per_second(self) -> int:
        return self.sample_rate_hz * self.sample_width_bytes * self.channels

    @property
    def duration_ms(self) -> int:
        if not self.raw_bytes or self.bytes_per_second <= 0:
            return 0
        return int(len(self.raw_bytes) / self.bytes_per_second * 1000)


class AudioPreprocessor(Protocol):
    """오디오 품질 개선을 수행하는 전처리기 인터페이스."""

    def preprocess(self, audio: AudioBuffer) -> AudioBuffer:
        """입력 오디오를 정제한 뒤 같은 형식의 오디오 버퍼를 반환한다."""
