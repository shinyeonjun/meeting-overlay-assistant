"""LLM 마크다운 정규화 규칙."""

from __future__ import annotations

import re

TOP_LEVEL_HEADING_PATTERN = re.compile(r"^\s*#\s+\S", re.MULTILINE)
SECTION_HEADING_PATTERN = re.compile(r"^\s*##\s+\S", re.MULTILINE)
LIST_ITEM_PATTERN = re.compile(r"^\s*(?:[-*]|\d+\.)\s+\S", re.MULTILINE)
SESSION_ID_PATTERN = re.compile(r"^\s*-\s*세션\s*ID\s*:", re.MULTILINE)
SECTION_SPLIT_PATTERN = re.compile(r"(?=^##\s+)", re.MULTILINE)
TOP_LEVEL_ITEM_PATTERN = re.compile(
    r"^\s*(?:[-*]\s+|\d+[.)]\s+|\[[ xX]\]\s+|-\s*\[[ xX]\]\s+)?(.+?)\s*$"
)

SESSION_ID_LINE_RULES = (
    re.compile(r"^\s*-?\s*session\s*id\s*:\s*(.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*-?\s*meeting\s*id\s*:\s*(.+?)\s*$", re.IGNORECASE),
)

TOP_LEVEL_HEADING_RULES = (
    (re.compile(r"^\s*#\s*(?:session|meeting)\s+report\b.*$", re.IGNORECASE), "# 회의 리포트"),
    (re.compile(r"^\s*#\s*report\b.*$", re.IGNORECASE), "# 회의 리포트"),
)

SECTION_HEADING_RULES = (
    (
        re.compile(r"^\s*##\s*(?:snapshot|overview|meeting overview)\s*$", re.IGNORECASE),
        "## 회의 개요",
    ),
    (
        re.compile(r"^\s*##\s*(?:questions?|open questions?)\s*$", re.IGNORECASE),
        "## 질문",
    ),
    (
        re.compile(r"^\s*##\s*(?:decisions?|decision log)\s*$", re.IGNORECASE),
        "## 결정 사항",
    ),
    (
        re.compile(r"^\s*##\s*(?:action items?|next steps?|todos?)\s*$", re.IGNORECASE),
        "## 액션 아이템",
    ),
    (
        re.compile(r"^\s*##\s*(?:risks?|concerns?)\s*$", re.IGNORECASE),
        "## 리스크",
    ),
    (
        re.compile(r"^\s*##\s*(?:transcript|reference transcript|notes?)\s*$", re.IGNORECASE),
        "## 참고 의사",
    ),
    (
        re.compile(
            r"^\s*##\s*(?:speaker insights?|insights?|observations?)\s*$",
            re.IGNORECASE,
        ),
        "## 발화자 기반 인사이트",
    ),
)

REQUIRED_SECTION_HEADINGS = (
    "## 회의 개요",
    "## 질문",
    "## 결정 사항",
    "## 액션 아이템",
    "## 리스크",
    "## 참고 의사",
    "## 발화자 기반 인사이트",
)

SECTION_STYLE_RULES = {
    "## 회의 개요": "bullet",
    "## 질문": "bullet",
    "## 결정 사항": "numbered",
    "## 액션 아이템": "checkbox",
    "## 리스크": "bullet",
    "## 참고 의사": "bullet",
    "## 발화자 기반 인사이트": "bullet",
}

