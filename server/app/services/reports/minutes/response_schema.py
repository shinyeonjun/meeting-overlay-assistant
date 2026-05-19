"""회의록 AI 응답 JSON schema."""

from __future__ import annotations

from typing import Any


LIST_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "text": {
            "type": "string",
            "description": "회의록에 표시할 공식 문서체 문장. 번호, 글머리표, Markdown, HTML을 포함하지 않는다.",
        },
        "important_phrases": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 3,
            "description": "text 안에 실제로 포함된 핵심 명사구. PDF/HTML 렌더러가 이 구절만 굵게 강조한다.",
        },
    },
    "required": ["text", "important_phrases"],
    "additionalProperties": False,
}

ACTION_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "task": {"type": "string"},
        "owner": {"type": ["string", "null"]},
        "due_date": {"type": ["string", "null"]},
        "status": {"type": ["string", "null"]},
        "note": {"type": ["string", "null"]},
    },
    "required": ["task", "owner", "due_date", "status", "note"],
    "additionalProperties": False,
}

SECTION_ITEM_SCHEMA: dict[str, Any] = {
    "type": "array",
    "items": LIST_ITEM_SCHEMA,
}

SECTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "time_range": {"type": ["string", "null"]},
        "background": SECTION_ITEM_SCHEMA,
        "opinions": SECTION_ITEM_SCHEMA,
        "review": SECTION_ITEM_SCHEMA,
        "direction": SECTION_ITEM_SCHEMA,
    },
    "required": ["title", "time_range", "background", "opinions", "review", "direction"],
    "additionalProperties": False,
}

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "agenda": {
            "type": "string",
        },
        "overview": {
            "type": "array",
            "items": {"type": "string"},
        },
        "sections": {
            "type": "array",
            "items": SECTION_SCHEMA,
        },
        "special_notes": {
            "type": "array",
            "items": LIST_ITEM_SCHEMA,
        },
        "decisions": {
            "type": "array",
            "items": LIST_ITEM_SCHEMA,
        },
        "follow_up": {
            "type": "array",
            "items": ACTION_ITEM_SCHEMA,
        },
    },
    "required": [
        "agenda",
        "overview",
        "sections",
        "decisions",
        "special_notes",
        "follow_up",
    ],
    "additionalProperties": False,
}
