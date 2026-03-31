"""실시간 질문 감지용 프롬프트 빌더."""

from __future__ import annotations

import json

from server.app.services.live_questions.models import LiveQuestionRequest


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
