"""도메인 공통 열거형."""

from enum import Enum, IntEnum


class SessionMode(str, Enum):
    """세션 모드."""

    MEETING = "meeting"
    LECTURE = "lecture"
    VIDEO = "video"


class AudioSource(str, Enum):
    """오디오 입력 소스."""

    MIC = "mic"
    SYSTEM_AUDIO = "system_audio"
    MIC_AND_AUDIO = "mic_and_audio"
    FILE = "file"


class SessionStatus(str, Enum):
    """세션 상태."""

    RUNNING = "running"
    ENDED = "ended"
    ARCHIVED = "archived"


class EventType(str, Enum):
    """회의 이벤트 유형."""

    TOPIC = "topic"
    QUESTION = "question"
    DECISION = "decision"
    ACTION_ITEM = "action_item"
    RISK = "risk"
    CONTEXT = "context"


class EventState(str, Enum):
    """회의 이벤트 상태."""

    OPEN = "open"
    CONFIRMED = "confirmed"
    CANDIDATE = "candidate"
    CLOSED = "closed"
    ACTIVE = "active"


class EventPriority(IntEnum):
    """회의 이벤트 우선순위."""

    NONE = 0
    LOW = 10
    TOPIC = 60
    QUESTION = 70
    RISK = 80
    DECISION = 85
    ACTION_ITEM = 90
