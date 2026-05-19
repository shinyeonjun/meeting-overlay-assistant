"""workspace summary 정제와 시간 포맷 유틸."""

from __future__ import annotations

from collections import Counter

from server.app.domain.shared.enums import EventType
from server.app.services.sessions.workspace_summary_models import (
    WorkspaceSummaryActionItem,
)
from server.app.services.sessions.workspace_summary_types import (
    _ChunkTopicCandidate,
)

_MEETING_TYPES = {
    "business_meeting",
    "brainstorming",
    "content",
    "casual",
}


def _select_topic_candidates_for_range(
    topic_candidates: list[dict[str, int | str]],
    *,
    start_ms: int,
    end_ms: int,
) -> list[dict[str, int | str]]:
    selected = [
        item
        for item in topic_candidates
        if _ranges_overlap(
            start_ms,
            end_ms,
            int(item.get("start_ms", 0)),
            int(item.get("end_ms", 0)),
        )
    ]
    return selected[:4] if selected else topic_candidates[:2]


def _clean_string_list(
    raw_value: object,
    *,
    limit: int,
    max_chars: int | None = None,
) -> list[str]:
    if not isinstance(raw_value, list):
        return []

    cleaned: list[str] = []
    for item in raw_value:
        text = str(item or "").strip()
        if not text:
            continue
        if max_chars is not None and len(text) > max_chars:
            continue
        if _looks_like_raw_transcript(text):
            continue
        cleaned.append(text)
        if len(cleaned) >= limit:
            break
    return _dedupe_strings(cleaned, limit=limit)


def _clean_int_list(
    raw_value: object,
    *,
    allowed_values: set[int],
    limit: int,
) -> list[int]:
    if not isinstance(raw_value, list):
        return []
    cleaned: list[int] = []
    for item in raw_value:
        if not isinstance(item, int) or item not in allowed_values:
            continue
        cleaned.append(item)
        if len(cleaned) >= limit:
            break
    return _dedupe_ints(cleaned, limit=limit)


def _clean_action_items(
    raw_value: object,
    *,
    limit: int,
    max_chars: int,
) -> list[WorkspaceSummaryActionItem]:
    if not isinstance(raw_value, list):
        return []

    cleaned: list[WorkspaceSummaryActionItem] = []
    for item in raw_value:
        if isinstance(item, WorkspaceSummaryActionItem):
            title = item.title.strip()
            owner = item.owner
            due_date = item.due_date
        elif isinstance(item, dict):
            title = str(item.get("title") or "").strip()
            owner = (
                str(item.get("owner")).strip()
                if item.get("owner") not in {None, ""}
                else None
            )
            due_date = (
                str(item.get("due_date")).strip()
                if item.get("due_date") not in {None, ""}
                else None
            )
        else:
            continue

        if not title or len(title) > max_chars or _looks_like_raw_transcript(title):
            continue

        cleaned.append(
            WorkspaceSummaryActionItem(
                title=title,
                owner=owner,
                due_date=due_date,
            )
        )
        if len(cleaned) >= limit:
            break
    return _dedupe_action_items(cleaned, limit=limit)


def _clean_chunk_topics(
    raw_value: object,
    *,
    fallback: list[_ChunkTopicCandidate],
    limit: int,
) -> list[_ChunkTopicCandidate]:
    if not isinstance(raw_value, list):
        return fallback

    topics: list[_ChunkTopicCandidate] = []
    seen: set[str] = set()
    for item in raw_value:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        summary = str(item.get("summary") or "").strip()
        normalized = " ".join(title.split()).lower()
        if not title or not summary or normalized in seen:
            continue
        if _looks_like_raw_transcript(title) or _looks_like_raw_transcript(summary):
            continue
        seen.add(normalized)
        topics.append(_ChunkTopicCandidate(title=title, summary=summary))
        if len(topics) >= limit:
            break
    return topics or fallback


def _dedupe_strings(values: list[str], *, limit: int) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        normalized = " ".join(value.split()).lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(value)
        if len(deduped) >= limit:
            break
    return deduped


def _dedupe_ints(values: list[int], *, limit: int) -> list[int]:
    seen: set[int] = set()
    deduped: list[int] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
        if len(deduped) >= limit:
            break
    return deduped


def _dedupe_action_items(
    values: list[WorkspaceSummaryActionItem],
    *,
    limit: int,
) -> list[WorkspaceSummaryActionItem]:
    seen: set[str] = set()
    deduped: list[WorkspaceSummaryActionItem] = []
    for value in values:
        normalized = " ".join(value.title.split()).lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(value)
        if len(deduped) >= limit:
            break
    return deduped


def _reduce_meeting_type(votes: list[str]) -> str:
    normalized_votes = [
        _normalize_meeting_type(value, "business_meeting")
        for value in votes
        if value
    ]
    if not normalized_votes:
        return "business_meeting"
    return Counter(normalized_votes).most_common(1)[0][0]


def _normalize_meeting_type(raw_value: object, fallback: str) -> str:
    value = str(raw_value or "").strip().lower()
    if value in _MEETING_TYPES:
        return value
    return fallback if fallback in _MEETING_TYPES else "business_meeting"


def _should_skip_event_title(title: str, event_type: EventType) -> bool:
    compact = " ".join(title.split())
    if not compact:
        return True
    max_chars_by_type = {
        EventType.TOPIC: 40,
        EventType.DECISION: 80,
        EventType.ACTION_ITEM: 80,
        EventType.QUESTION: 90,
        EventType.RISK: 90,
    }
    if len(compact) > max_chars_by_type.get(event_type, 90):
        return True
    if compact.count(" ") >= 18:
        return True
    return _looks_like_raw_transcript(compact)


def _looks_like_raw_transcript(text: str) -> bool:
    compact = " ".join(text.split())
    if not compact:
        return True
    if len(compact) > 120:
        return True
    if compact.endswith(("?", "??")) and compact.count(" ") >= 8:
        return True
    filler_keywords = (
        "그냥 농담",
        "오버한 거",
        "죄송합니다",
        "아 네",
        "아니요",
        "고맙습니다",
        "감사합니다",
    )
    return any(keyword in compact for keyword in filler_keywords) and compact.count(" ") >= 4


def _ranges_overlap(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
    return start_a <= end_b and start_b <= end_a


def _format_ms(value: int) -> str:
    total_seconds = max(int(value // 1000), 0)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def _format_range(start_ms: int, end_ms: int) -> str:
    return f"{_format_ms(start_ms)} - {_format_ms(end_ms)}"
