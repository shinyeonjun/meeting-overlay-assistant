"""assistant 질문 계획 JSON schema."""

from __future__ import annotations

from typing import Any

QUERY_PLAN_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "search_query": {
            "type": "string",
            "description": "RAG 검색에 사용할 짧고 구체적인 한국어 검색 질의",
        },
        "answer_focus": {
            "type": "string",
            "description": "최종 답변이 집중해야 할 관점",
        },
        "retrieval_sources": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["knowledge", "sessions"],
            },
            "description": "사용할 근거 소스. 회의 내용은 knowledge, 회의 목록/날짜/메타데이터는 sessions",
        },
        "target_dates": {
            "type": "array",
            "items": {"type": "string"},
            "description": "현재 KST 기준으로 해석한 YYYY-MM-DD 날짜 목록. 없으면 빈 배열",
        },
        "time_scope": {
            "type": "string",
            "description": "질문에 포함된 시간 범위 해석. 없으면 빈 문자열",
        },
        "time_expression": {
            "type": "string",
            "description": "사용자가 쓴 원래 상대/절대 시간 표현. 없으면 빈 문자열",
        },
        "resolved_time_range": {
            "type": "string",
            "description": "현재 KST 기준으로 해석한 날짜/시간 범위. 명확하지 않으면 빈 문자열",
        },
        "needs_clarification": {
            "type": "boolean",
            "description": "검색 전에 사용자에게 질문을 명확히 해야 하는지 여부",
        },
        "clarification_question": {
            "type": ["string", "null"],
            "description": "needs_clarification=true일 때 사용자에게 물어볼 짧은 질문",
        },
        "confidence": {
            "type": "number",
            "description": "계획 신뢰도. 0에서 1 사이",
        },
    },
    "required": [
        "search_query",
        "answer_focus",
        "retrieval_sources",
        "target_dates",
        "time_scope",
        "time_expression",
        "resolved_time_range",
        "needs_clarification",
        "clarification_question",
        "confidence",
    ],
    "additionalProperties": False,
}
