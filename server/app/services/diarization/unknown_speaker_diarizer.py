"""화자 분리를 수행하지 않는 기본 화자 분리기."""

from __future__ import annotations

from dataclasses import dataclass

from server.app.services.audio.preprocessing.audio_preprocessing import AudioBuffer
from server.app.services.diarization.speaker_diarizer import SpeakerSegment


@dataclass(frozen=True)
class UnknownSpeakerDiarizerConfig:
    """기본 화자 라벨 설정."""

    speaker_label: str = "화자-미분류"


class UnknownSpeakerDiarizer:
    """전체 오디오를 하나의 화자로 간주하는 기본 구현."""

    def __init__(self, config: UnknownSpeakerDiarizerConfig) -> None:
        self._config = config

    def diarize(self, audio: AudioBuffer) -> list[SpeakerSegment]:
        if not audio.raw_bytes:
            return []
        return [
            SpeakerSegment(
                speaker_label=self._config.speaker_label,
                start_ms=0,
                end_ms=max(audio.duration_ms, 1),
            )
        ]

