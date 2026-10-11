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


class PostProcessingStatus(str, Enum):
    """세션 후처리 상태. 값은 DB와 API에서 쓰는 문자열과 같다."""

    NOT_STARTED = "not_started"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


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
    CONTEXT = "context"


class EventState(str, Enum):
    """회의 이벤트 상태."""

    OPEN = "open"
    CONFIRMED = "confirmed"
    CANDIDATE = "candidate"
    ANSWERED = "answered"
    UNRESOLVED = "unresolved"
    UPDATED = "updated"
    MONITORING = "monitoring"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ACTIVE = "active"


class EventPriority(IntEnum):
    """이전 이벤트 우선순위 값 호환용 enum."""

    NONE = 0
    LOW = 10
    TOPIC = 60
    QUESTION = 70
    RISK = 80
    DECISION = 85
    ACTION_ITEM = 90
