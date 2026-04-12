"""오디오 입력을 발화 세그먼트로 분리하는 유틸리티."""

from __future__ import annotations

from collections import deque

from server.app.services.audio.segmentation.models import (
    AudioSegmenter,
    FrameSlice,
    SpeechSegment,
    VadSegmenterConfig,
)
from server.app.services.audio.segmentation.vad_lifecycle import (
    finalize_segment,
    should_finalize,
    start_segment,
)
from server.app.services.audio.segmentation.vad_math import (
    calculate_rms,
    classify_frame,
    now_ms,
    update_noise_floor,
)


class SpeechSegmenter:
    """텍스트나 미리 분리된 오디오를 그대로 하나의 세그먼트로 취급한다."""

    def split(self, chunk: bytes) -> list[SpeechSegment]:
        if not chunk:
            return []
        now = now_ms()
        return [SpeechSegment(raw_bytes=chunk, start_ms=now, end_ms=now + 1000)]


class VadSpeechSegmenter:
    """PCM 오디오를 에너지 기반으로 감지해서 발화 세그먼트로 묶는다."""

    def __init__(self, config: VadSegmenterConfig) -> None:
        self._config = config
        self._cursor_ms = now_ms()
        self._remainder = bytearray()
        self._pre_roll: deque[FrameSlice] = deque(maxlen=config.pre_roll_frames or 1)
        self._activation_buffer: list[FrameSlice] = []
        self._active_frames: list[FrameSlice] = []
        self._active_voiced_frames = 0
        self._silence_run_frames = 0
        self._pending_early_eou_hint = False
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

    def _build_frame(self, frame_bytes: bytes) -> FrameSlice:
        start_ms = self._cursor_ms
        end_ms = start_ms + self._config.frame_duration_ms
        self._cursor_ms = end_ms
        rms = self._calculate_rms(frame_bytes)
        is_voiced = self._classify_frame(rms, active=bool(self._active_frames))
        return FrameSlice(
            raw_bytes=frame_bytes,
            start_ms=start_ms,
            end_ms=end_ms,
            rms=rms,
            is_voiced=is_voiced,
        )

    def _consume_frame(self, frame: FrameSlice) -> SpeechSegment | None:
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

    def _consume_active_frame(self, frame: FrameSlice) -> SpeechSegment | None:
        frame_is_voiced = self._classify_frame(frame.rms, active=True)
        self._active_frames.append(frame)
        if frame_is_voiced:
            self._active_voiced_frames += 1
            self._silence_run_frames = 0
            self._pending_early_eou_hint = False
        else:
            self._silence_run_frames += 1
            if self._silence_run_frames >= self._config.early_post_roll_frames:
                self._pending_early_eou_hint = True

        if self._should_finalize():
            return self._finalize_segment()
        return None

    def consume_early_eou_hint(self) -> bool:
        """live 확정용 early EOU 힌트를 1회성으로 소비한다."""

        if not self._pending_early_eou_hint:
            return False
        self._pending_early_eou_hint = False
        return True

    def _start_segment(self) -> None:
        start_segment(self)

    def _should_finalize(self) -> bool:
        return should_finalize(self)

    def _finalize_segment(self) -> SpeechSegment | None:
        return finalize_segment(self)

    def _classify_frame(self, rms: float, *, active: bool) -> bool:
        return classify_frame(
            self._config,
            self._noise_floor_rms,
            rms,
            active=active,
        )

    def _update_noise_floor(self, rms: float) -> None:
        self._noise_floor_rms = update_noise_floor(
            self._config,
            self._noise_floor_rms,
            rms,
        )

    def _calculate_rms(self, frame_bytes: bytes) -> float:
        return calculate_rms(self._config, frame_bytes)


__all__ = [
    "AudioSegmenter",
    "SpeechSegment",
    "SpeechSegmenter",
    "VadSegmenterConfig",
    "VadSpeechSegmenter",
]
