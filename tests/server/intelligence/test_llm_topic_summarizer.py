"""LLM topic summarizer 테스트."""

from __future__ import annotations

from server.app.services.sessions.topic_helpers.heuristic import TopicHeuristicSummarizer
from server.app.services.sessions.topic_helpers.llm import LLMTopicSummarizer


class _FakeCompletionClient:
    def __init__(self, responses: list[object]) -> None:
        self._responses = list(responses)
        self.calls: list[str] = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return str(response)


def test_llm_topic_summarizer가_요약값을_정규화하고_캐시한다() -> None:
    client = _FakeCompletionClient(["현재 주제: 로그인 오류 원인 분석"])
    summarizer = LLMTopicSummarizer(client)
    topic_texts = [
        "로그인 오류 원인을 먼저 분석해보죠",
        "로그인 화면에서 오류가 반복됩니다",
    ]

    first = summarizer.summarize("session-1", topic_texts)
    second = summarizer.summarize("session-1", topic_texts)

    assert first == "로그인 오류 원인 분석"
    assert second == "로그인 오류 원인 분석"
    assert len(client.calls) == 1


def test_llm_topic_summarizer가_실패하면_heuristic으로_fallback한다() -> None:
    topic_texts = [
        "배포 일정 언제 확정하나요",
        "배포 일정이 다음 주로 가는지 확인합시다",
        "일정 리스크를 같이 보죠",
    ]
    client = _FakeCompletionClient([RuntimeError("llm failed")])
    summarizer = LLMTopicSummarizer(client)
    expected = TopicHeuristicSummarizer().summarize(
        session_id="session-2",
        topic_texts=topic_texts,
        fallback_topic="fallback",
    )

    summary = summarizer.summarize("session-2", topic_texts, fallback_topic="fallback")

    assert summary == expected


def test_llm_topic_summarizer가_입력이_없으면_fallback을_반환한다() -> None:
    client = _FakeCompletionClient([])
    summarizer = LLMTopicSummarizer(client)

    summary = summarizer.summarize("session-3", [], fallback_topic="기본 주제")

    assert summary == "기본 주제"
    assert client.calls == []
