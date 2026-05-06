"""assistant 답변 응답 파서."""

from __future__ import annotations

import json


def normalize_answer(response_text: str) -> str:
    """LLM 응답이 JSON 또는 일반 텍스트여도 최종 답변 문자열만 추출한다."""

    answer = response_text.strip()
    if not answer:
        return ""
    try:
        parsed = json.loads(answer)
    except json.JSONDecodeError:
        return answer
    if isinstance(parsed, dict):
        value = parsed.get("answer") or parsed.get("response") or parsed.get("content")
        if isinstance(value, str) and value.strip():
            return value.strip()
        return ""
    return answer
