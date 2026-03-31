"""실시간 질문 요청 디스패처 테스트."""

from __future__ import annotations

from server.app.services.live_questions.models import LiveQuestionItem
from server.app.services.live_questions.question_dispatch_service import (
    LiveQuestionDispatchService,
)


class _FakeQueue:
    def __init__(self) -> None:
        self.requests = []

    def publish_request(self, request):
        self.requests.append(request)
        return True


class _FakeStateStore:
    def list_open_questions(self, session_id: str):
        return [
            LiveQuestionItem(
                id="q-open-1",
                summary="기존 질문",
            )
        ]


class _FakeUtterance:
    def __init__(self, *, session_id: str, utterance_id: str, text: str) -> None:
        self.session_id = session_id
        self.id = utterance_id
        self.text = text
        self.end_ms = 1000
        self.confidence = 0.8
        self.speaker_label = None


class TestLiveQuestionDispatchService:
    def test_submit된_최근_발화들로_request를_발행한다(self):
        queue = _FakeQueue()
        service = LiveQuestionDispatchService(
            queue=queue,
            state_store=_FakeStateStore(),
            debounce_ms=1000,
            window_size=3,
        )
        try:
            service.submit(
                _FakeUtterance(
                    session_id="session-1",
                    utterance_id="utt-1",
                    text="첫 번째 질문 후보",
                )
            )
            service.submit(
                _FakeUtterance(
                    session_id="session-1",
                    utterance_id="utt-2",
                    text="두 번째 질문 후보",
                )
            )

            service._flush_session(session_id="session-1")

            assert len(queue.requests) == 1
            request = queue.requests[0]
            assert request.session_id == "session-1"
            assert [item.id for item in request.utterances] == ["utt-1", "utt-2"]
            assert [item.summary for item in request.open_questions] == ["기존 질문"]
        finally:
            service.shutdown()
