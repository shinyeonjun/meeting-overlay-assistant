"""공용 테스트 입력 데이터."""

from __future__ import annotations

from backend.app.domain.models.utterance import Utterance


SESSION_TITLE = "테스트 회의"
TOPIC_TEXT = "로그인 오류 원인을 먼저 분석해보죠."
QUESTION_TEXT = "이거 사파리에서만 재현되는 거 맞아요?"
DECISION_TEXT = "이번 배포에서는 이 수정은 제외합시다."
ACTION_TEXT = "민수가 금요일까지 수정안 정리해 주세요."
RISK_TEXT = "이 일정이면 QA가 밀려서 배포가 지연될 위험이 있어요."


def build_utterance(text: str, confidence: float = 0.95) -> Utterance:
    """공용 테스트 발화를 생성한다."""
    return Utterance.create(
        session_id="session-test",
        seq_num=1,
        start_ms=0,
        end_ms=1000,
        text=text,
        confidence=confidence,
    )
