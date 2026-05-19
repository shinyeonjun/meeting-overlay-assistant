"""assistant 답변 응답 파서."""

from __future__ import annotations

from server.app.services.analysis.llm.json_response import load_json_object_response


def normalize_answer(response_text: str) -> str:
    """LLM 응답이 JSON 또는 일반 텍스트여도 최종 답변 문자열만 추출한다."""

    answer = response_text.strip()
    if not answer:
        return ""
    if not _looks_like_json_answer(answer):
        return answer
    try:
        parsed = load_json_object_response(answer)
    except (TypeError, ValueError):
        return answer
    value = parsed.get("answer") or parsed.get("response") or parsed.get("content")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return ""


def _looks_like_json_answer(answer: str) -> bool:
    return answer.startswith("{") or answer.startswith("```")
