from __future__ import annotations

from server.app.services.live_questions.models import LiveQuestionUtterance
from server.app.services.live_questions.question_dispatch_service import (
    LiveQuestionDispatchService,
)
from server.app.services.live_questions.question_text_normalizer import (
    QuestionTextNormalizer,
    load_question_text_normalizer_from_env,
)


class _FakeQueue:
    def __init__(self) -> None:
        self.requests = []

    def publish_request(self, request) -> bool:
        self.requests.append(request)
        return True


class _FakeStateStore:
    def list_open_questions(self, session_id: str):
        return []


class _FakeUtterance:
    def __init__(self, *, session_id: str, utterance_id: str, text: str) -> None:
        self.session_id = session_id
        self.id = utterance_id
        self.text = text
        self.end_ms = 1000
        self.confidence = 0.8
        self.speaker_label = None


def test_question_text_normalizer_replaces_longer_terms_first():
    normalizer = QuestionTextNormalizer(
        replacements=(
            ("캡스 라이브", "CAPS Live"),
            ("캡스", "CAPS"),
        )
    )
    utterance = LiveQuestionUtterance(
        id="utt-1",
        text="캡스 라이브 질문 lane 테스트",
        speaker_label=None,
        timestamp_ms=1000,
        confidence=0.9,
    )

    normalized = normalizer.normalize_utterance(utterance)

    assert normalized.text == "CAPS Live 질문 lane 테스트"


def test_load_question_text_normalizer_from_env_reads_json_dict(monkeypatch):
    monkeypatch.setenv(
        "LIVE_QUESTION_TERM_ALIASES_JSON",
        '{"큐웬":"Qwen","캡스":"CAPS"}',
    )

    normalizer = load_question_text_normalizer_from_env()

    assert set(normalizer.replacements) == {("캡스", "CAPS"), ("큐웬", "Qwen")}


def test_dispatch_service_applies_question_text_normalizer_before_publish():
    queue = _FakeQueue()
    service = LiveQuestionDispatchService(
        queue=queue,
        state_store=_FakeStateStore(),
        debounce_ms=1000,
        window_size=3,
        text_normalizer=QuestionTextNormalizer(replacements=(("캡스", "CAPS"),)),
    )
    try:
        service.submit(
            _FakeUtterance(
                session_id="session-1",
                utterance_id="utt-1",
                text="캡스 질문 lane 확인",
            )
        )

        service._flush_session(session_id="session-1")

        assert len(queue.requests) == 1
        assert queue.requests[0].utterances[0].text == "CAPS 질문 lane 확인"
    finally:
        service.shutdown()
