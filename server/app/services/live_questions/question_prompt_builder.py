"""실시간 질문 감지 전용 프롬프트 빌더."""

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
                    "op": {"type": "string", "enum": ["add"]},
                    "summary": {"type": "string"},
                    "confidence": {"type": ["number", "null"]},
                    "evidence_utterance_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "target_question_id": {"type": "null"},
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
    """질문 후보 window에서 실제 질문만 고르는 system prompt를 반환한다."""

    return (
        "너는 한국어 회의 발화에서 질문 또는 명확한 확인 요청만 감지하는 실시간 필터다. "
        "입력 window는 넓게 잡힌 후보라서 질문이 아닐 수 있다. "
        "리스크, 액션아이템, 결정사항, 답변 여부는 판단하지 않는다. "
        "반드시 JSON만 반환한다. 최상위 객체는 {\"operations\": [...]} 형식이다. "
        "새 질문이나 답변이 필요한 확인 요청이 확실할 때만 op=add를 반환하고, 아니면 빈 배열을 반환한다."
    )


def build_question_analysis_prompt(request: LiveQuestionRequest) -> str:
    """질문 감지 전용 분석 프롬프트를 만든다."""

    payload = {
        "goal": "최근 안정화된 회의 발화 window에서 새 질문 또는 답변이 필요한 확인 요청만 찾아낸다.",
        "rules": [
            "반드시 JSON만 반환한다.",
            "operations 배열에는 op=add만 넣을 수 있다.",
            "답변됨, 미답변, close, resolved 같은 상태 추적은 하지 않는다.",
            "리스크, 액션아이템, 결정사항은 실시간으로 추출하지 않는다.",
            "입력은 넓은 후보라서 질문이 아닐 수 있다. 질문이 아니면 operations를 빈 배열로 반환한다.",
            "물음표가 없어도 상대의 답변이나 확인이 필요한 문장은 질문 후보로 본다.",
            "단순 상태 공유, 진행 멘트, 이미 확정된 결정, 일반 업무 지시는 제외한다.",
            "summary는 실제 질문/확인 요청 내용을 짧은 한국어 문장으로 쓴다.",
            "summary에 '새 질문', '질문 여부' 같은 메타 표현을 쓰지 않는다.",
            "이미 open_questions에 같은 질문이 있으면 중복 add하지 않는다.",
            "target_question_id는 항상 null이다.",
            "evidence_utterance_ids에는 질문 판단의 근거가 된 utterance id를 넣는다.",
        ],
        "request": request.to_payload(),
        "response_schema": {
            "operations": [
                {
                    "op": "add",
                    "summary": "실제 질문 또는 확인 요청 요약",
                    "confidence": "0.0 ~ 1.0",
                    "evidence_utterance_ids": ["utterance id"],
                    "target_question_id": None,
                    "speaker_label": "있으면 사용, 없으면 null",
                    "reason": "짧은 판단 근거",
                }
            ]
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_question_analysis_warmup_prompt() -> str:
    """질문 감지 모델 warm-up용 최소 프롬프트를 반환한다."""

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
