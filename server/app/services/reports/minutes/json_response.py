"""회의록 호환용 LLM JSON 응답 파싱 helper."""

from __future__ import annotations

from server.app.services.analysis.llm.json_response import load_json_object_response


def load_json_response(response_text: str) -> dict[str, object]:
    """기존 회의록 모듈 import 경로를 유지한다."""

    return load_json_object_response(response_text)
