"""화자 분리 공통 모델과 인터페이스."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend.app.services.audio.preprocessing.audio_preprocessing import AudioBuffer


@dataclass(frozen=True)
class SpeakerSegment:
    """화자 라벨이 붙은 발화 구간."""

    speaker_label: str
    start_ms: int
    end_ms: int


class SpeakerDiarizer(Protocol):
    """오디오에서 화자별 발화 구간을 추정하는 인터페이스."""

    def diarize(self, audio: AudioBuffer) -> list[SpeakerSegment]:
        """입력 오디오를 화자 구간 목록으로 변환한다."""

