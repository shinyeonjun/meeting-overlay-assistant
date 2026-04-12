"""공통 영역의 test live question state store 동작을 검증한다."""
from __future__ import annotations

from server.app.domain.shared.enums import EventState
from server.app.services.live_questions.models import (
    LiveQuestionOperation,
    LiveQuestionResult,
)
from server.app.services.live_questions.question_state_store import LiveQuestionStateStore


class TestLiveQuestionStateStore:
    """LiveQuestionStateStore 동작을 검증한다."""
    def test_add_연산은_open_question을_추가한다(self):
        store = LiveQuestionStateStore()
        result = LiveQuestionResult(
            session_id="session-1",
            window_id="window-1",
            operations=(
                LiveQuestionOperation(
                    op="add",
                    summary="배포 일정은 언제 확정되나요?",
                    confidence=0.91,
                    evidence_utterance_ids=("utt-1",),
                ),
            ),
        )

        changed = store.apply_result(result)
        open_questions = store.list_open_questions("session-1")

        assert len(changed) == 1
        assert changed[0].state == EventState.OPEN
        assert changed[0].title == "배포 일정은 언제 확정되나요?"
        assert len(open_questions) == 1
        assert open_questions[0].summary == "배포 일정은 언제 확정되나요?"

    def test_close_연산은_open_question을_answered로_닫는다(self):
        store = LiveQuestionStateStore()
        added = store.apply_result(
            LiveQuestionResult(
                session_id="session-2",
                window_id="window-add",
                operations=(
                    LiveQuestionOperation(
                        op="add",
                        summary="일정 확정은 언제 되나요?",
                        evidence_utterance_ids=("utt-2",),
                    ),
                ),
            )
        )
        question_id = added[0].id

        changed = store.apply_result(
            LiveQuestionResult(
                session_id="session-2",
                window_id="window-close",
                operations=(
                    LiveQuestionOperation(
                        op="close",
                        target_question_id=question_id,
                        reason="answered",
                    ),
                ),
            )
        )

        assert len(changed) == 1
        assert changed[0].id == question_id
        assert changed[0].state == EventState.ANSWERED
        assert store.list_open_questions("session-2") == []

    def test_같은_질문_summary는_중복_add하지_않는다(self):
        store = LiveQuestionStateStore()
        first = LiveQuestionResult(
            session_id="session-3",
            window_id="window-1",
            operations=(
                LiveQuestionOperation(
                    op="add",
                    summary="다음 배포는 언제죠?",
                    evidence_utterance_ids=("utt-a",),
                ),
            ),
        )
        second = LiveQuestionResult(
            session_id="session-3",
            window_id="window-2",
            operations=(
                LiveQuestionOperation(
                    op="add",
                    summary="다음 배포는 언제죠?",
                    evidence_utterance_ids=("utt-b",),
                ),
            ),
        )

        first_changed = store.apply_result(first)
        second_changed = store.apply_result(second)

        assert len(first_changed) == 1
        assert second_changed == []
        assert len(store.list_open_questions("session-3")) == 1
