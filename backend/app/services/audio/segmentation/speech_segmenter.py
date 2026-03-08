"""오디오 입력을 발화 세그먼트로 분리하는 유틸리티."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from time import time
from typing import Protocol


def _now_ms() -> int:
    return int(time() * 1000)


@dataclass(frozen=True)
class SpeechSegment:
    """STT에 전달할 발화 세그먼트."""

    raw_bytes: bytes
    start_ms: int
    end_ms: int


class AudioSegmenter(Protocol):
    """오디오 chunk를 발화 세그먼트 목록으로 바꾸는 인터페이스."""

    def split(self, chunk: bytes) -> list[SpeechSegment]:
        """입력 chunk를 하나 이상의 발화 세그먼트로 나눈다."""


class SpeechSegmenter:
    """텍스트나 이미 분리된 오디오를 그대로 하나의 세그먼트로 취급한다."""

    def split(self, chunk: bytes) -> list[SpeechSegment]:
        if not chunk:
            return []
        now = _now_ms()
        return [SpeechSegment(raw_bytes=chunk, start_ms=now, end_ms=now + 1000)]


@dataclass(frozen=True)
class VadSegmenterConfig:
    """에너지 기반 VAD 세그먼터 설정."""

    sample_rate_hz: int = 16000
    sample_width_bytes: int = 2
    channels: int = 1
    frame_duration_ms: int = 30
    pre_roll_ms: int = 300
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
    def min_speech_frames(self) -> int:
        return max(int(self.min_speech_ms / self.frame_duration_ms), 1)

    @property
    def max_segment_frames(self) -> int:
        return max(int(self.max_segment_ms / self.frame_duration_ms), 1)


@dataclass(frozen=True)
class _FrameSlice:
    raw_bytes: bytes
    start_ms: int
    end_ms: int
    rms: float
    is_voiced: bool


class VadSpeechSegmenter:
    """PCM 오디오를 에너지 기반으로 감지해서 발화 세그먼트로 묶는다."""

    def __init__(self, config: VadSegmenterConfig) -> None:
        self._config = config
        self._cursor_ms = _now_ms()
        self._remainder = bytearray()
        self._pre_roll: deque[_FrameSlice] = deque(maxlen=config.pre_roll_frames or 1)
        self._activation_buffer: list[_FrameSlice] = []
        self._active_frames: list[_FrameSlice] = []
        self._active_voiced_frames = 0
        self._silence_run_frames = 0
        self._noise_floor_rms = max(config.rms_threshold * 0.5, 0.0005)

    def split(self, chunk: bytes) -> list[SpeechSegment]:
        if not chunk:
            return []

        self._remainder.extend(chunk)
        segments: list[SpeechSegment] = []

        while len(self._remainder) >= self._config.bytes_per_frame:
            frame_bytes = bytes(self._remainder[: self._config.bytes_per_frame])
            del self._remainder[: self._config.bytes_per_frame]

            frame = self._build_frame(frame_bytes)
            segment = self._consume_frame(frame)
            if segment is not None:
                segments.append(segment)

        return segments

    def _build_frame(self, frame_bytes: bytes) -> _FrameSlice:
        start_ms = self._cursor_ms
        end_ms = start_ms + self._config.frame_duration_ms
        self._cursor_ms = end_ms
        rms = self._calculate_rms(frame_bytes)
        is_voiced = self._classify_frame(rms, active=bool(self._active_frames))
        return _FrameSlice(
            raw_bytes=frame_bytes,
            start_ms=start_ms,
            end_ms=end_ms,
            rms=rms,
            is_voiced=is_voiced,
        )

    def _consume_frame(self, frame: _FrameSlice) -> SpeechSegment | None:
        if self._active_frames:
            return self._consume_active_frame(frame)

        self._pre_roll.append(frame)
        if frame.is_voiced:
            self._activation_buffer.append(frame)
            if len(self._activation_buffer) >= self._config.min_activation_frames:
                self._start_segment()
        else:
            self._update_noise_floor(frame.rms)
            self._activation_buffer.clear()
        return None

    def _consume_active_frame(self, frame: _FrameSlice) -> SpeechSegment | None:
        frame_is_voiced = self._classify_frame(frame.rms, active=True)
        self._active_frames.append(frame)
        if frame_is_voiced:
            self._active_voiced_frames += 1
            self._silence_run_frames = 0
        else:
            self._silence_run_frames += 1

        if self._should_finalize():
            return self._finalize_segment()
        return None

    def _start_segment(self) -> None:
        self._active_frames = list(self._pre_roll)
        self._active_voiced_frames = sum(1 for frame in self._active_frames if frame.is_voiced)
        self._silence_run_frames = 0
        self._activation_buffer.clear()

    def _should_finalize(self) -> bool:
        if len(self._active_frames) >= self._config.max_segment_frames:
            return True
        return self._silence_run_frames >= self._config.post_roll_frames

    def _finalize_segment(self) -> SpeechSegment | None:
        frames = self._active_frames
        voiced_frames = self._active_voiced_frames

        self._active_frames = []
        self._active_voiced_frames = 0
        self._silence_run_frames = 0
        self._pre_roll.clear()

        if not frames or voiced_frames < self._config.min_speech_frames:
            return None

        voiced_ratio = voiced_frames / len(frames)
        if voiced_ratio < self._config.min_voiced_ratio:
            return None

        return SpeechSegment(
            raw_bytes=b"".join(frame.raw_bytes for frame in frames),
            start_ms=frames[0].start_ms,
            end_ms=frames[-1].end_ms,
        )

    def _classify_frame(self, rms: float, *, active: bool) -> bool:
        threshold = max(
            self._config.rms_threshold,
            self._noise_floor_rms * self._config.adaptive_threshold_multiplier,
        )
        if active:
            threshold *= self._config.active_threshold_ratio
        return rms >= threshold

    def _update_noise_floor(self, rms: float) -> None:
        alpha = self._config.adaptive_noise_floor_alpha
        self._noise_floor_rms = (alpha * self._noise_floor_rms) + ((1 - alpha) * rms)

    def _calculate_rms(self, frame_bytes: bytes) -> float:
        np = _import_numpy()

        if self._config.sample_width_bytes != 2:
            raise ValueError("현재 VAD 세그먼터는 16-bit PCM만 지원합니다.")

        samples = np.frombuffer(frame_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        if self._config.channels > 1:
            samples = samples.reshape(-1, self._config.channels).mean(axis=1)
        if samples.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(np.square(samples))))


def _import_numpy():
    import numpy as np

    return np
