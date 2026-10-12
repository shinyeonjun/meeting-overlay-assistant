"""화자 분리 공통 모델과 인터페이스.

정의는 reporting이 소유한 포트에 있고, post_processing은 같은 이름으로 재노출한다.
"""

from __future__ import annotations

from server.app.contexts.reporting import (
    SpeakerDiarizer,
    SpeakerSegment,
)


__all__ = [
    "SpeakerDiarizer",
    "SpeakerSegment",
]
