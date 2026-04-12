"""오디오 영역의 vad lifecycle 서비스를 제공한다."""
from __future__ import annotations

from server.app.services.audio.segmentation.models import SpeechSegment


def start_segment(segmenter) -> None:
    """pre-roll과 activation buffer를 합쳐 active segment를 시작한다."""

    frames = []
    seen_frame_starts: set[int] = set()

    for frame in [*segmenter._pre_roll, *segmenter._activation_buffer]:
        if frame.start_ms in seen_frame_starts:
            continue
        frames.append(frame)
        seen_frame_starts.add(frame.start_ms)

    segmenter._active_frames = frames
    segmenter._active_voiced_frames = sum(
        1 for frame in segmenter._active_frames if frame.is_voiced
    )
    segmenter._silence_run_frames = 0
    segmenter._activation_buffer.clear()


def should_finalize(segmenter) -> bool:
    """현재 active segment를 종료해야 하는지 판단한다."""

    if len(segmenter._active_frames) >= segmenter._config.max_segment_frames:
        return True
    return segmenter._silence_run_frames >= segmenter._config.post_roll_frames


def finalize_segment(segmenter) -> SpeechSegment | None:
    """active frames를 SpeechSegment로 마감한다."""

    frames = segmenter._active_frames
    voiced_frames = segmenter._active_voiced_frames

    segmenter._active_frames = []
    segmenter._active_voiced_frames = 0
    segmenter._silence_run_frames = 0
    segmenter._pending_early_eou_hint = False
    segmenter._pre_roll.clear()

    if not frames or voiced_frames < segmenter._config.min_speech_frames:
        return None

    voiced_ratio = voiced_frames / len(frames)
    if voiced_ratio < segmenter._config.min_voiced_ratio:
        return None

    return SpeechSegment(
        raw_bytes=b"".join(frame.raw_bytes for frame in frames),
        start_ms=frames[0].start_ms,
        end_ms=frames[-1].end_ms,
    )
