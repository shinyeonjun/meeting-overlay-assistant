"""오디오 세그멘테이션 모델과 설정."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SpeechSegment:
    """STT로 전달할 발화 세그먼트."""

    raw_bytes: bytes
    start_ms: int
    end_ms: int


class AudioSegmenter(Protocol):
    """오디오 chunk를 발화 세그먼트 목록으로 바꾸는 인터페이스."""

    def split(self, chunk: bytes) -> list[SpeechSegment]:
        """입력 chunk를 하나 이상의 발화 세그먼트로 나눈다."""


@dataclass(frozen=True)
class VadSegmenterConfig:
    """에너지 기반 VAD 세그먼터 설정."""

    sample_rate_hz: int = 16000
    sample_width_bytes: int = 2
    channels: int = 1
    frame_duration_ms: int = 30
    pre_roll_ms: int = 300
    early_post_roll_ms: int = 300
    post_roll_ms: int = 450
    min_speech_ms: int = 240
    max_segment_ms: int = 5000
    min_activation_frames: int = 2
    rms_threshold: float = 0.01
    adaptive_noise_floor_alpha: float = 0.92
    adaptive_threshold_multiplier: float = 1.9
    active_threshold_ratio: float = 0.8
    min_voiced_ratio: float = 0.18

    @property
    def frame_sample_count(self) -> int:
        return max(int(self.sample_rate_hz * (self.frame_duration_ms / 1000)), 1)

    @property
    def bytes_per_frame(self) -> int:
        return self.frame_sample_count * self.sample_width_bytes * self.channels

    @property
    def pre_roll_frames(self) -> int:
        return max(int(self.pre_roll_ms / self.frame_duration_ms), 0)

    @property
    def post_roll_frames(self) -> int:
        return max(int(self.post_roll_ms / self.frame_duration_ms), 1)

    @property
    def early_post_roll_frames(self) -> int:
        early_frames = max(int(self.early_post_roll_ms / self.frame_duration_ms), 1)
        return min(early_frames, self.post_roll_frames)

    @property
    def min_speech_frames(self) -> int:
        return max(int(self.min_speech_ms / self.frame_duration_ms), 1)

    @property
    def max_segment_frames(self) -> int:
        return max(int(self.max_segment_ms / self.frame_duration_ms), 1)


@dataclass(frozen=True)
class FrameSlice:
    """VAD가 처리하는 프레임 단위 조각."""

    raw_bytes: bytes
    start_ms: int
    end_ms: int
    rms: float
    is_voiced: bool
