"""assistant 최근 대화 문맥 정리."""

from __future__ import annotations

MAX_HISTORY_ITEMS = 6
MAX_HISTORY_CONTENT_CHARS = 500

_ALLOWED_ROLES = {"user", "assistant"}
_FOLLOW_UP_TERMS = (
    "그거",
    "그건",
    "그걸",
    "그게",
    "그때",
    "그 내용",
    "그 사람",
    "이거",
    "이건",
    "방금",
    "앞에서",
    "위에서",
    "더 자세히",
    "자세히",
    "누가",
    "왜",
    "언제",
)


def normalize_conversation_history(items) -> tuple[dict[str, str], ...]:
    """API 입력이나 클라이언트 상태에서 최근 대화만 안전하게 추린다."""

    normalized: list[dict[str, str]] = []
    for item in items or ():
        role = _read_value(item, "role").casefold()
        content = _read_value(item, "content")
        if role not in _ALLOWED_ROLES or not content:
            continue
        normalized.append(
            {
                "role": role,
                "content": _truncate(content, MAX_HISTORY_CONTENT_CHARS),
            }
        )
    return tuple(normalized[-MAX_HISTORY_ITEMS:])


def render_conversation_history(items) -> str:
    """프롬프트에 넣을 최근 대화 요약 텍스트를 만든다."""

    normalized = normalize_conversation_history(items)
    if not normalized:
        return ""
    lines = []
    for item in normalized:
        label = "사용자" if item["role"] == "user" else "챗봇"
        lines.append(f"- {label}: {item['content']}")
    return "\n".join(lines)


def build_contextual_search_query(
    *,
    query: str,
    conversation_history,
) -> str:
    """후속 질문이면 직전 사용자 질문을 검색 질의에 붙인다."""

    normalized_query = " ".join(query.split())
    if not normalized_query or not _looks_like_follow_up(normalized_query):
        return normalized_query

    previous_user_query = _latest_user_query(conversation_history)
    if not previous_user_query:
        return normalized_query
    if previous_user_query in normalized_query:
        return normalized_query
    return f"{previous_user_query} {normalized_query}"


def _looks_like_follow_up(query: str) -> bool:
    compact = query.replace(" ", "").casefold()
    return any(term.replace(" ", "").casefold() in compact for term in _FOLLOW_UP_TERMS)


def _latest_user_query(items) -> str:
    for item in reversed(normalize_conversation_history(items)):
        if item["role"] == "user":
            return item["content"]
    return ""


def _read_value(item, key: str) -> str:
    if isinstance(item, dict):
        value = item.get(key)
    else:
        value = getattr(item, key, None)
    return " ".join(str(value or "").split())


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"
