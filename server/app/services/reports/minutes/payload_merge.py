"""회의록 AI chunk payload 병합과 품질 보정 helper."""

from __future__ import annotations

from server.app.services.reports.minutes.normalization import (
    clean_text,
    limit_text,
    normalize_merge_key,
    normalize_optional,
    normalize_owner,
    normalize_status,
)
from server.app.services.reports.minutes.payload_items import (
    dedupe_strings,
    dedupe_text_item_payloads,
    extract_string_items,
    extract_text_item_payloads,
    iter_raw_list,
    iter_raw_sections,
)


SECTION_TEXT_FIELDS = ("background", "opinions", "review", "direction")


def find_payload_quality_issue(
    payload: dict[str, object],
    *,
    transcript_segments: int,
) -> str | None:
    """회의록 payload에서 사용자에게 보여줄 본문 누락 문제를 찾는다."""

    if transcript_segments < 3:
        return None
    if _has_section_content(payload.get("sections")):
        return None
    if _has_substantive_content_outside_sections(payload):
        return (
            "회의내용 sections가 비어 있습니다. 보조 필드에 실질 내용이 있으면 "
            "그 근거가 되는 논의 내용을 sections에 작성해야 합니다."
        )
    return None


def repair_payload_sections_from_supporting_fields(
    payload: dict[str, object],
) -> dict[str, object]:
    """보조 필드만 있고 sections가 비어 있으면 회의내용 section을 보정한다."""

    if _has_section_content(payload.get("sections")):
        return payload

    background = [
        {"text": text, "important_phrases": []}
        for text in extract_string_items(payload.get("overview"))[:3]
    ]
    review = extract_text_item_payloads(payload.get("special_notes"))[:5]
    direction = [
        *extract_text_item_payloads(payload.get("decisions")),
        *_extract_follow_up_direction_items(payload.get("follow_up")),
    ][:5]

    if not any((background, review, direction)):
        return payload

    title = _derive_repaired_section_title(payload)
    repaired = dict(payload)
    repaired["sections"] = [
        {
            "title": limit_text(title, 80) or title,
            "time_range": None,
            "background": background,
            "opinions": [],
            "review": review,
            "direction": direction,
        }
    ]
    return repaired


def _derive_repaired_section_title(payload: dict[str, object]) -> str:
    for agenda in extract_string_items(payload.get("agenda")):
        if agenda:
            return agenda
    section_titles = [
        clean_text(section.get("title"))
        for section in iter_raw_sections(payload.get("sections"))
        if clean_text(section.get("title"))
    ]
    if section_titles:
        return section_titles[0]
    for overview in extract_string_items(payload.get("overview")):
        if overview:
            return overview
    return "주요 논의"


def _extract_follow_up_direction_items(value: object) -> list[dict[str, object]]:
    """follow_up만 있는 응답도 회의내용 보정에 활용한다."""

    items: list[dict[str, object]] = []
    for raw_item in iter_raw_list(value):
        if not isinstance(raw_item, dict):
            continue
        task = clean_text(raw_item.get("task"))
        if not task:
            continue
        items.append({"text": limit_text(task, 180), "important_phrases": []})
    return items


def merge_chunk_payloads(payloads: list[dict[str, object]]) -> dict[str, object]:
    """분할 분석된 회의록 payload들을 하나의 payload로 병합한다."""

    return {
        "agenda": _merge_agenda(payloads),
        "overview": _merge_string_arrays(payloads, "overview", limit=6),
        "sections": _merge_sections(payloads),
        "decisions": _merge_object_list_items(payloads, "decisions", limit=8),
        "special_notes": _merge_object_list_items(payloads, "special_notes", limit=8),
        "follow_up": _merge_action_items(payloads, limit=8),
    }


def _has_section_content(value: object) -> bool:
    for raw_section in iter_raw_sections(value):
        for field in SECTION_TEXT_FIELDS:
            if extract_text_item_payloads(raw_section.get(field)):
                return True
    return False


def _has_substantive_content_outside_sections(payload: dict[str, object]) -> bool:
    if extract_string_items(payload.get("overview")):
        return True
    if extract_text_item_payloads(payload.get("decisions")):
        return True
    if extract_text_item_payloads(payload.get("special_notes")):
        return True
    follow_up = payload.get("follow_up")
    if isinstance(follow_up, list):
        for raw_item in follow_up:
            if isinstance(raw_item, dict) and clean_text(raw_item.get("task")):
                return True
    return False


def _merge_agenda(payloads: list[dict[str, object]]) -> str:
    for payload in payloads:
        agenda = clean_text(payload.get("agenda"))
        if agenda:
            return limit_text(agenda, 80) or agenda
    section_titles = [
        clean_text(section.get("title"))
        for payload in payloads
        for section in iter_raw_sections(payload.get("sections"))
    ]
    if section_titles:
        return " / ".join(dedupe_strings(section_titles, limit=3))
    return ""


def _merge_sections(payloads: list[dict[str, object]]) -> list[dict[str, object]]:
    merged_by_key: dict[str, dict[str, object]] = {}
    ordered_keys: list[str] = []
    for payload in payloads:
        for section in iter_raw_sections(payload.get("sections")):
            title = clean_text(section.get("title"))
            if not title:
                continue
            key = normalize_merge_key(title)
            if key not in merged_by_key:
                merged_by_key[key] = {
                    "title": limit_text(title, 120) or title,
                    "time_range": normalize_optional(section.get("time_range")),
                    "background": [],
                    "opinions": [],
                    "review": [],
                    "direction": [],
                }
                ordered_keys.append(key)
            target = merged_by_key[key]
            if target.get("time_range") is None:
                target["time_range"] = normalize_optional(section.get("time_range"))
            for field in SECTION_TEXT_FIELDS:
                target[field] = dedupe_text_item_payloads(
                    [*target[field], *extract_text_item_payloads(section.get(field))],
                    limit=5,
                )

    return [merged_by_key[key] for key in ordered_keys[:8]]


def _merge_string_arrays(
    payloads: list[dict[str, object]],
    key: str,
    *,
    limit: int,
) -> list[str]:
    items: list[str] = []
    for payload in payloads:
        items.extend(extract_string_items(payload.get(key)))
    return dedupe_strings(items, limit=limit)


def _merge_object_list_items(
    payloads: list[dict[str, object]],
    key: str,
    *,
    limit: int,
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for payload in payloads:
        items.extend(extract_text_item_payloads(payload.get(key)))
    return dedupe_text_item_payloads(items, limit=limit)


def _merge_action_items(
    payloads: list[dict[str, object]],
    *,
    limit: int,
) -> list[dict[str, str | None]]:
    items: list[dict[str, str | None]] = []
    seen: set[str] = set()
    for payload in payloads:
        for raw_item in iter_raw_list(payload.get("follow_up")):
            if not isinstance(raw_item, dict):
                continue
            task = clean_text(raw_item.get("task"))
            if not task:
                continue
            key = normalize_merge_key(task)
            if key in seen:
                continue
            seen.add(key)
            items.append(
                {
                    "task": limit_text(task, 180),
                    "owner": normalize_owner(raw_item.get("owner")),
                    "due_date": normalize_optional(raw_item.get("due_date")),
                    "status": normalize_status(raw_item.get("status")),
                    "note": limit_text(clean_text(raw_item.get("note")), 180),
                }
            )
            if len(items) >= limit:
                return items
    return items
