"""실시간 질문 감지용 프롬프트 빌더."""

from __future__ import annotations

import json
from typing import Any

from server.app.services.live_questions.models import LiveQuestionRequest


LIVE_QUESTION_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "operations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "op": {"type": "string", "enum": ["add", "close"]},
                    "summary": {"type": ["string", "null"]},
                    "confidence": {"type": ["number", "null"]},
                    "evidence_utterance_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "target_question_id": {"type": ["string", "null"]},
                    "speaker_label": {"type": ["string", "null"]},
                    "reason": {"type": ["string", "null"]},
                },
                "required": [
                    "op",
                    "summary",
                    "confidence",
                    "evidence_utterance_ids",
                    "target_question_id",
                    "speaker_label",
                    "reason",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["operations"],
    "additionalProperties": False,
}


def build_question_analysis_system_prompt() -> str:
    """질문 추출 전용 system prompt를 반환한다."""

    return (
        "너는 한국어 회의 발화에서 열린 질문만 골라내는 실시간 질문 추출기다. "
        "반드시 JSON만 반환한다. "
        "operations 배열만 사용한다. "
        "질문이 확실하지 않으면 빈 배열을 반환한다. "
        "새 질문은 add, 기존 열린 질문이 명확히 답변되었을 때만 close를 사용한다. "
        "summary는 메타 표현이 아닌 실제 질문 요약으로 짧게 쓴다."
    )


def build_question_analysis_prompt(request: LiveQuestionRequest) -> str:
    """질문 전용 분석 프롬프트를 만든다."""

    payload = {
        "goal": "최근 회의 발화에서 새 질문이 생겼는지 찾고, 기존 열린 질문이 답변됐는지 판단한다.",
        "rules": [
            "반드시 JSON만 반환한다.",
            "최상위 객체는 반드시 {\"operations\": [...]} 형태만 사용한다.",
            "response, data, result 같은 감싸는 키를 추가하지 않는다.",
            "질문이 분명하지 않으면 operations를 빈 배열로 반환한다.",
            "새 질문은 op=add로 반환한다.",
            "열린 질문이 없으면 op=close를 반환하지 않는다.",
            "기존 열린 질문이 답변되거나 닫힌 것으로 보이면 op=close로 반환한다.",
            "summary는 발화의 핵심 명사를 유지한 한국어 한 줄 요약으로 작성한다.",
            "summary에 '새 질문', '질문이 분명하지 않음', '불명확' 같은 메타 표현을 쓰지 않는다.",
            "확신이 낮으면 close를 남발하지 않는다.",
        ],
        "request": request.to_payload(),
        "response_schema": {
            "operations": [
                {
                    "op": "add | close",
                    "summary": "새 질문일 때만 사용",
                    "confidence": "0.0 ~ 1.0",
                    "evidence_utterance_ids": ["u_1"],
                    "target_question_id": "close일 때 닫을 질문 id",
                    "speaker_label": "있으면 사용",
                    "reason": "close일 때 answered 같은 짧은 사유",
                }
            ]
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_question_analysis_warmup_prompt() -> str:
    """질문 추출 모델 warm-up용 최소 프롬프트를 반환한다."""

    payload = {
        "goal": "모델 warm-up",
        "request": {
            "session_id": "warmup",
            "window_id": "warmup",
            "utterances": [],
            "open_questions": [],
            "created_at_ms": 0,
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
