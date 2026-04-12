"""화자 분리 서비스가 따라야 할 최소 계약을 정의한다.

실제 구현은 pyannote, 규칙 기반 분리기, 테스트 더블 등으로 달라질 수 있다.
이 모듈은 공통으로 사용하는 segment 데이터 구조와 diarize 인터페이스만
가볍게 고정한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from server.app.services.audio.preprocessing.audio_preprocessing import AudioBuffer


@dataclass(frozen=True)
class SpeakerSegment:
    """화자 라벨이 붙은 발화 구간.

    start/end는 밀리초 기준이며, downstream STT/노트 후처리는 이 범위를
    기준으로 오디오를 잘라 다시 전사하거나 병합한다.
    """

    speaker_label: str
    start_ms: int
    end_ms: int


class SpeakerDiarizer(Protocol):
    """오디오에서 화자별 발화 구간을 추정하는 인터페이스."""

    def diarize(self, audio: AudioBuffer) -> list[SpeakerSegment]:
        """입력 오디오를 시간순 화자 구간 목록으로 변환한다."""
