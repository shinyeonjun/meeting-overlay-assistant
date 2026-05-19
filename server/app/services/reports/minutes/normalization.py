"""회의록 AI payload 정규화 helper."""

from __future__ import annotations


def clean_text(value: object) -> str:
    """값을 회의록 payload 비교/저장에 사용할 단일 공백 문자열로 정리한다."""

    return " ".join(str(value or "").split())


def limit_text(value: str | None, limit: int) -> str | None:
    """문자열을 지정 길이로 줄이고 말줄임표를 붙인다."""

    if not value:
        return None
    if len(value) <= limit:
        return value
    return f"{value[: limit - 1].rstrip()}…"


def normalize_optional(value: object) -> str | None:
    """없음/미정 계열 값을 None으로 정규화한다."""

    cleaned = clean_text(value)
    if not cleaned or cleaned in {
        "-",
        "없음",
        "미기록",
        "null",
        "None",
        "open",
        "pending",
        "대기",
        "미정",
    }:
        return None
    return cleaned


def normalize_owner(value: object) -> str | None:
    """담당자 값을 정규화하고 시스템 화자 라벨은 제거한다."""

    owner = normalize_optional(value)
    if not owner or owner.upper().startswith("SPEAKER_"):
        return None
    return owner


def normalize_status(value: object) -> str | None:
    """action item 상태 값을 한국어 상태명으로 정규화한다."""

    status = normalize_optional(value)
    if not status:
        return None
    status_by_value = {
        "done": "완료",
        "completed": "완료",
        "complete": "완료",
        "resolved": "완료",
        "in_progress": "진행 중",
        "progress": "진행 중",
    }
    return status_by_value.get(status.lower(), status)


def normalize_merge_key(value: str) -> str:
    """중복 제거에 사용할 공백 없는 소문자 key를 만든다."""

    return "".join(clean_text(value).lower().split())


def value_of(value: object) -> str:
    """Enum 값이면 value를, 아니면 문자열 값을 반환한다."""

    return str(getattr(value, "value", value))
