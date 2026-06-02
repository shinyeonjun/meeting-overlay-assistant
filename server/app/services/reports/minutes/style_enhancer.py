"""회의록 정본 문서의 인라인 강조 구절을 2차 AI 패스로 보강한다."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import replace

from server.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)
from server.app.services.reports.composition.inline_formatting import strip_inline_marks
from server.app.services.reports.composition.report_document import (
    ReportDocumentV1,
    ReportListItem,
    ReportSection,
)
from server.app.services.reports.minutes.json_response import load_json_response


STYLE_ENHANCEMENT_SYSTEM_PROMPT = """
너는 회의록 문서의 시각 스타일을 직접 만들지 않는다.
이미 작성된 회의록 문장을 읽고, 렌더러가 강조할 짧은 핵심 구절만 JSON으로 고른다.

규칙:
- CSS, HTML, Markdown, 색상명, 글꼴명, 표 레이아웃 지시는 절대 쓰지 않는다.
- important_phrases에는 item text 안에 실제로 포함된 구절만 정확히 복사한다.
- 구절은 항목당 최대 3개, 각 구절은 2~24자 정도의 짧은 명사구나 핵심 표현으로 제한한다.
- 문장 전체를 강조 대상으로 고르지 않는다.
- 결정사항, 리스크, 확인 필요, 담당자/기한, 공유 전 확인 내용은 우선 강조한다.
- 강조할 필요가 없으면 빈 배열을 반환한다.
- 입력에 없는 item id를 만들지 않는다.
""".strip()


STYLE_ENHANCEMENT_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "important_phrases": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 3,
                    },
                },
                "required": ["id", "important_phrases"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}

_STYLE_BATCH_SIZE = 12
_MAX_STYLE_ITEMS = 32


def enhance_report_document_styles(
    *,
    completion_client: LLMCompletionClient,
    config,
    logger: logging.Logger,
    session_id: str,
    document: ReportDocumentV1,
) -> ReportDocumentV1:
    """2차 LLM 패스로 important_phrases만 갱신한다."""

    indexed_items = _index_document_items(document)
    if not indexed_items:
        return document
    selected_items = _select_style_items(indexed_items)
    if not selected_items:
        return document

    started_at = time.perf_counter()
    logger.info(
        "회의록 AI 스타일 분석 시작: session_id=%s model=%s items=%s selected_items=%s batches=%s",
        session_id,
        config.model,
        len(indexed_items),
        len(selected_items),
        len(_chunk_items(selected_items, batch_size=_STYLE_BATCH_SIZE)),
    )
    phrase_map: dict[str, tuple[str, ...]] = {}
    for batch_index, batch in enumerate(
        _chunk_items(selected_items, batch_size=_STYLE_BATCH_SIZE),
        start=1,
    ):
        prompt = _build_style_prompt(document, batch)
        try:
            response_text = completion_client.complete(
                prompt,
                system_prompt=STYLE_ENHANCEMENT_SYSTEM_PROMPT,
                response_schema=(
                    STYLE_ENHANCEMENT_RESPONSE_SCHEMA
                    if getattr(config, "use_response_schema", True)
                    else None
                ),
                keep_alive=config.keep_alive,
            )
            phrase_map.update(_parse_style_phrase_map(response_text, batch))
        except Exception:
            logger.exception(
                "회의록 AI 스타일 분석 batch 실패: session_id=%s model=%s batch=%s prompt_chars=%s",
                session_id,
                config.model,
                batch_index,
                len(prompt),
            )

    enhanced_document = _apply_style_phrase_map(document, phrase_map)
    logger.info(
        "회의록 AI 스타일 분석 완료: session_id=%s model=%s elapsed=%.2fs styled_items=%s response_items=%s",
        session_id,
        config.model,
        time.perf_counter() - started_at,
        sum(1 for phrases in phrase_map.values() if phrases),
        len(phrase_map),
    )
    return enhanced_document


def _build_style_prompt(
    document: ReportDocumentV1,
    indexed_items: list[dict[str, object]],
) -> str:
    payload = {
        "title": document.title,
        "instruction": (
            "items의 각 text에서 렌더러가 강조할 important_phrases만 고른다. "
            "반드시 JSON object만 반환한다."
        ),
        "items": indexed_items,
        "output_shape": {
            "items": [
                {
                    "id": "입력 item id",
                    "important_phrases": ["text 안에 실제로 포함된 짧은 구절"],
                }
            ]
        },
    }
    return json.dumps(payload, ensure_ascii=False)


def _index_document_items(document: ReportDocumentV1) -> list[dict[str, object]]:
    indexed: list[dict[str, object]] = []

    for index, item in enumerate(document.agenda):
        _append_indexed_item(indexed, f"agenda.{index}", "안건", item)
    for section_index, section in enumerate(document.sections):
        for field_name, label in (
            ("background", "논의 배경"),
            ("opinions", "주요 의견"),
            ("review", "검토 내용"),
            ("direction", "정리된 방향"),
            ("discussion", "회의내용"),
            ("decisions", "섹션 결정사항"),
            ("special_notes", "섹션 특이사항"),
        ):
            for item_index, item in enumerate(getattr(section, field_name)):
                _append_indexed_item(
                    indexed,
                    f"sections.{section_index}.{field_name}.{item_index}",
                    f"{section.title} / {label}",
                    item,
                )
    if not document.sections:
        for index, item in enumerate(document.discussion):
            _append_indexed_item(indexed, f"discussion.{index}", "회의내용", item)
    for index, item in enumerate(document.decisions):
        _append_indexed_item(indexed, f"decisions.{index}", "결정사항", item)
    for index, item in enumerate(document.questions):
        _append_indexed_item(indexed, f"questions.{index}", "남은 질문", item)
    for index, item in enumerate(document.risks):
        _append_indexed_item(indexed, f"risks.{index}", "특이사항/리스크", item)
    return indexed


def _append_indexed_item(
    indexed: list[dict[str, object]],
    item_id: str,
    section_label: str,
    item: ReportListItem,
) -> None:
    text = strip_inline_marks(item.text).strip()
    if not text:
        return
    indexed.append(
        {
            "id": item_id,
            "section": section_label,
            "text": text,
            "current_important_phrases": list(item.important_phrases),
            "priority": _style_item_priority(item_id, section_label, text),
        }
    )


def _style_item_priority(item_id: str, section_label: str, text: str) -> int:
    priority = 0
    if item_id.startswith(("decisions.", "risks.")):
        priority += 90
    if ".direction." in item_id:
        priority += 80
    if ".review." in item_id:
        priority += 70
    if ".opinions." in item_id:
        priority += 60
    if ".background." in item_id:
        priority += 30
    if any(keyword in text for keyword in ("결정", "확정", "리스크", "주의", "확인", "담당", "기한", "공유")):
        priority += 35
    if 18 <= len(text) <= 160:
        priority += 10
    if "특이사항" in section_label or "리스크" in section_label:
        priority += 20
    return priority


def _select_style_items(indexed_items: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        indexed_items,
        key=lambda item: (
            -int(item.get("priority") or 0),
            str(item.get("id") or ""),
        ),
    )[:_MAX_STYLE_ITEMS]


def _chunk_items(
    items: list[dict[str, object]],
    *,
    batch_size: int,
) -> list[list[dict[str, object]]]:
    return [
        items[index : index + batch_size]
        for index in range(0, len(items), max(batch_size, 1))
    ]


def _parse_style_phrase_map(
    response_text: str,
    indexed_items: list[dict[str, object]],
) -> dict[str, tuple[str, ...]]:
    payload = load_json_response(response_text)
    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        return {}

    text_by_id = {
        str(item["id"]): str(item["text"])
        for item in indexed_items
        if "id" in item and "text" in item
    }
    phrase_map: dict[str, tuple[str, ...]] = {}
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        item_id = str(raw_item.get("id") or "")
        if item_id not in text_by_id:
            continue
        raw_phrases = raw_item.get("important_phrases")
        if not isinstance(raw_phrases, list):
            continue
        phrase_map[item_id] = _valid_phrases(text_by_id[item_id], raw_phrases)
    return phrase_map


def _valid_phrases(text: str, raw_phrases: list[object]) -> tuple[str, ...]:
    phrases: list[str] = []
    seen: set[str] = set()
    stripped_text = text.strip()
    for raw_phrase in raw_phrases:
        phrase = " ".join(strip_inline_marks(str(raw_phrase)).split())
        if not phrase or len(phrase) < 2 or len(phrase) > 24:
            continue
        if phrase == stripped_text or phrase not in text:
            continue
        key = phrase.casefold()
        if key in seen:
            continue
        seen.add(key)
        phrases.append(phrase)
        if len(phrases) >= 3:
            break
    return tuple(phrases)


def _apply_style_phrase_map(
    document: ReportDocumentV1,
    phrase_map: dict[str, tuple[str, ...]],
) -> ReportDocumentV1:
    if not phrase_map:
        return document

    return replace(
        document,
        agenda=_map_items("agenda", document.agenda, phrase_map),
        sections=tuple(
            _map_section(section_index, section, phrase_map)
            for section_index, section in enumerate(document.sections)
        ),
        discussion=_map_items("discussion", document.discussion, phrase_map),
        decisions=_map_items("decisions", document.decisions, phrase_map),
        questions=_map_items("questions", document.questions, phrase_map),
        risks=_map_items("risks", document.risks, phrase_map),
    )


def _map_section(
    section_index: int,
    section: ReportSection,
    phrase_map: dict[str, tuple[str, ...]],
) -> ReportSection:
    return replace(
        section,
        background=_map_items(
            f"sections.{section_index}.background",
            section.background,
            phrase_map,
        ),
        opinions=_map_items(
            f"sections.{section_index}.opinions",
            section.opinions,
            phrase_map,
        ),
        review=_map_items(
            f"sections.{section_index}.review",
            section.review,
            phrase_map,
        ),
        direction=_map_items(
            f"sections.{section_index}.direction",
            section.direction,
            phrase_map,
        ),
        discussion=_map_items(
            f"sections.{section_index}.discussion",
            section.discussion,
            phrase_map,
        ),
        decisions=_map_items(
            f"sections.{section_index}.decisions",
            section.decisions,
            phrase_map,
        ),
        special_notes=_map_items(
            f"sections.{section_index}.special_notes",
            section.special_notes,
            phrase_map,
        ),
    )


def _map_items(
    prefix: str,
    items: tuple[ReportListItem, ...],
    phrase_map: dict[str, tuple[str, ...]],
) -> tuple[ReportListItem, ...]:
    return tuple(
        replace(item, important_phrases=phrase_map[item_id])
        if (item_id := f"{prefix}.{index}") in phrase_map
        else item
        for index, item in enumerate(items)
    )
