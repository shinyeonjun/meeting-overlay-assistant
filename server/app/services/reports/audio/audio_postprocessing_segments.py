"""오디오 후처리 segment 정규화와 PCM slicing helper."""

from __future__ import annotations

from server.app.services.audio.preprocessing.audio_preprocessing import AudioBuffer
from server.app.services.diarization.speaker_diarizer import SpeakerSegment


MIN_POSTPROCESSING_SEGMENT_MS = 120
MERGEABLE_SAME_SPEAKER_GAP_MS = 180


def slice_pcm_bytes(audio: AudioBuffer, start_ms: int, end_ms: int) -> bytes:
    """밀리초 구간을 PCM sample 경계에 맞춰 잘라낸다."""

    bytes_per_ms = audio.bytes_per_second / 1000
    start_index = max(int(start_ms * bytes_per_ms), 0)
    end_index = max(int(end_ms * bytes_per_ms), start_index)

    sample_size = max(audio.sample_width_bytes * audio.channels, 1)
    aligned_start = start_index - (start_index % sample_size)
    aligned_end = end_index - (end_index % sample_size)
    return audio.raw_bytes[aligned_start:aligned_end]


def normalize_diarized_segments(
    diarized_segments: list[SpeakerSegment],
) -> list[SpeakerSegment]:
    """짧게 끊긴 동일 화자 구간을 후처리에 적합하게 병합한다."""

    if not diarized_segments:
        return []

    normalized: list[SpeakerSegment] = []
    for segment in diarized_segments:
        if not normalized:
            normalized.append(segment)
            continue

        previous = normalized[-1]
        gap_ms = max(0, segment.start_ms - previous.end_ms)
        if (
            previous.speaker_label == segment.speaker_label
            and gap_ms <= MERGEABLE_SAME_SPEAKER_GAP_MS
        ):
            normalized[-1] = SpeakerSegment(
                speaker_label=previous.speaker_label,
                start_ms=previous.start_ms,
                end_ms=max(previous.end_ms, segment.end_ms),
            )
            continue
        normalized.append(segment)

    return normalized
