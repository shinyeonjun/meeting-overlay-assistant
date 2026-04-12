"""도메인 공통 enum 정의."""

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

    DRAFT = "draft"
    RUNNING = "running"
    ENDED = "ended"
    ARCHIVED = "archived"


class EventType(str, Enum):
    """회의 이벤트 타입."""

    TOPIC = "topic"
    QUESTION = "question"
    DECISION = "decision"
    ACTION_ITEM = "action_item"
    RISK = "risk"


class EventState(str, Enum):
    """회의 이벤트 상태."""

    ACTIVE = "active"
    OPEN = "open"
    ANSWERED = "answered"
    CONFIRMED = "confirmed"
    UPDATED = "updated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class EventPriority(IntEnum):
    """이전 이벤트 우선순위 값 호환용 enum."""

    NONE = 0
    LOW = 10
    TOPIC = 60
    QUESTION = 70
    RISK = 80
    DECISION = 85
    ACTION_ITEM = 90
