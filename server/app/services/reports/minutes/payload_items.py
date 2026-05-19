"""회의록 AI payload list item 정리 helper."""

from __future__ import annotations

from server.app.services.reports.minutes.normalization import (
    clean_text,
    limit_text,
    normalize_merge_key,
)

TEXT_VALUE_KEYS = (
    "text",
    "content",
    "summary",
    "description",
    "note",
    "title",
    "task",
)
PHRASE_VALUE_KEYS = (
    "important_phrases",
    "highlight_phrases",
    "highlights",
    "keywords",
)


def iter_raw_sections(value: object) -> list[dict[str, object]]:
    """payload의 sections 값에서 dict section만 반환한다."""

    if isinstance(value, dict):
        return [value]
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def iter_raw_list(value: object) -> list[object]:
    """payload 값이 list이면 그대로, 아니면 빈 list를 반환한다."""

    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def extract_string_items(value: object) -> list[str]:
    """payload list에서 비어 있지 않은 문자열 항목만 정리해 반환한다."""

    items: list[str] = []
    for raw_item in iter_raw_list(value):
        text = _extract_text_value(raw_item)
        if text:
            items.append(text)
    return items


def extract_text_item_payloads(value: object) -> list[dict[str, object]]:
    """문자열/dict list item을 표준 text item payload로 정규화한다."""

    items: list[dict[str, object]] = []
    for raw_item in iter_raw_list(value):
        item = coerce_text_item_payload(raw_item)
        if item is not None:
            items.append(item)
    return items


def coerce_text_item_payload(raw_item: object) -> dict[str, object] | None:
    """문자열 또는 dict item을 text/important_phrases payload로 정규화한다."""

    if isinstance(raw_item, dict):
        text = _extract_text_value(raw_item)
        phrase_source = _extract_phrase_value(raw_item)
    else:
        text = clean_text(raw_item)
        phrase_source = []

    if not text:
        return None

    limited_text = limit_text(text, 220) or text
    return {
        "text": limited_text,
        "important_phrases": list(
            parse_important_phrases(phrase_source, limited_text)
        ),
    }


def _extract_text_value(raw_item: object) -> str:
    """LLM이 text 대신 content/summary 같은 키를 쓴 경우까지 텍스트를 찾는다."""

    if not isinstance(raw_item, dict):
        return clean_text(raw_item)

    for key in TEXT_VALUE_KEYS:
        text = clean_text(raw_item.get(key))
        if text:
            return text
    return ""


def _extract_phrase_value(raw_item: dict[str, object]) -> object:
    for key in PHRASE_VALUE_KEYS:
        value = raw_item.get(key)
        if value:
            return value
    return []


def dedupe_text_item_payloads(
    items: list[dict[str, object]],
    *,
    limit: int,
) -> list[dict[str, object]]:
    """text item payload list에서 같은 텍스트를 제거하고 개수를 제한한다."""

    result: list[dict[str, object]] = []
    seen: set[str] = set()
    for raw_item in items:
        item = coerce_text_item_payload(raw_item)
        if item is None:
            continue
        text = clean_text(item.get("text"))
        if not text:
            continue
        key = normalize_merge_key(text)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
        if len(result) >= limit:
            break
    return result


def parse_important_phrases(value: object, text: str) -> tuple[str, ...]:
    """본문에 실제 포함된 짧은 강조 구절만 추출한다."""

    if not isinstance(value, list):
        return ()

    phrases: list[str] = []
    seen: set[str] = set()
    clean_item_text = clean_text(text)
    for raw_phrase in value:
        phrase = clean_text(raw_phrase)
        if (
            not phrase
            or len(phrase) < 2
            or len(phrase) > 24
            or phrase == clean_item_text
            or phrase not in clean_item_text
        ):
            continue
        key = normalize_merge_key(phrase)
        if key in seen:
            continue
        seen.add(key)
        phrases.append(phrase)
        if len(phrases) >= 3:
            break
    return tuple(phrases)


def dedupe_strings(items: list[str], *, limit: int) -> list[str]:
    """문자열 list에서 같은 내용을 제거하고 개수를 제한한다."""

    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        cleaned = limit_text(clean_text(item), 220)
        if not cleaned:
            continue
        key = normalize_merge_key(cleaned)
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
        if len(result) >= limit:
            break
    return result
