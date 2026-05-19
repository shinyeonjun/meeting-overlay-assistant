"""노트 transcript 후보정 LLM 응답 파싱과 안전장치."""

from __future__ import annotations

import re
from dataclasses import dataclass

from server.app.services.analysis.llm.json_response import load_json_object_response


CORRECTION_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "corrected_text": {"type": "string"},
        "changed": {"type": "boolean"},
        "risk_flags": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["corrected_text", "changed", "risk_flags"],
    "additionalProperties": False,
}

HIGH_RISK_TOKEN_PATTERN = re.compile(
    r"(\d+[./:-]\d+|\d+원|\d+만원|v\d+(?:\.\d+)*|버전\s*\d+(?:\.\d+)*)",
    re.IGNORECASE,
)
_DIGIT_PATTERN = re.compile(r"\d+")


@dataclass(frozen=True)
class CorrectionResponse:
    corrected_text: str
    risk_flags: list[str]


def parse_correction_response(
    response_text: str,
    *,
    fallback_text: str,
) -> CorrectionResponse:
    """LLM 응답 JSON을 보수적으로 파싱한다."""

    try:
        payload = load_json_object_response(response_text)
    except (TypeError, ValueError):
        return CorrectionResponse(
            corrected_text=fallback_text,
            risk_flags=["invalid_json"],
        )

    corrected_text = str(payload.get("corrected_text") or "").strip()
    if not corrected_text:
        corrected_text = fallback_text
    risk_flags = [
        str(flag).strip()
        for flag in (payload.get("risk_flags") or [])
        if str(flag).strip()
    ]
    return CorrectionResponse(
        corrected_text=corrected_text,
        risk_flags=risk_flags,
    )


def sanitize_correction(*, raw_text: str, corrected_text: str) -> str:
    """숫자/금액/버전 등 위험 정보가 바뀌거나 과도하게 길어진 보정을 되돌린다."""

    normalized = corrected_text.strip()
    if not normalized:
        return raw_text
    if HIGH_RISK_TOKEN_PATTERN.search(raw_text):
        if _normalize_digits(raw_text) != _normalize_digits(normalized):
            return raw_text
    if len(normalized) > max(len(raw_text) * 3, len(raw_text) + 30):
        return raw_text
    return normalized


def _normalize_digits(text: str) -> tuple[str, ...]:
    return tuple(_DIGIT_PATTERN.findall(text))
