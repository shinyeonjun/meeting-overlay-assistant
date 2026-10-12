"""reporting이 소비하는 화자 분리 포트.

reporting은 화자 분리 구현(post_processing)에 의존하지 않고, 필요한 형태만 여기서 정의한다.
post_processing은 이 모델을 재사용해 구현체를 만든다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from server.app.contexts.live_capture import AudioBuffer


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
