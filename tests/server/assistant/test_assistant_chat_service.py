"""assistant chat 서비스 테스트."""

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from server.app.domain.retrieval import RetrievalSearchResult
from server.app.services.assistant import AssistantChatService, AssistantTimeContext


def _fixed_time_context() -> AssistantTimeContext:
    return AssistantTimeContext(
        now=datetime(2026, 4, 30, 6, 0, 0, tzinfo=timezone(timedelta(hours=9))),
        timezone_name="Asia/Seoul",
    )


def _plan_response(
    search_query: str,
    *,
    answer_focus: str = "질문에 직접 답변",
    retrieval_sources: list[str] | None = None,
    target_dates: list[str] | None = None,
) -> str:
    return json.dumps(
        {
            "search_query": search_query,
            "answer_focus": answer_focus,
            "retrieval_sources": retrieval_sources or ["knowledge"],
            "target_dates": target_dates or [],
            "time_scope": "현재 KST 기준 최근 회의",
            "time_expression": "최근",
            "resolved_time_range": "2026-04-30 06:00:00 KST 기준",
            "needs_clarification": False,
            "clarification_question": None,
            "confidence": 0.8,
        },
        ensure_ascii=False,
    )


class _FakeRetrievalQueryService:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        return self.results


class _FakeSessionService:
    def __init__(self, sessions):
        self.sessions = sessions
        self.calls = []

    def list_sessions(self, **kwargs):
        self.calls.append(kwargs)
        return self.sessions


class _FakeCompletionClient:
    def __init__(self, responses):
        self.responses = list(responses if isinstance(responses, list) else [responses])
        self.calls = []

    def complete(self, prompt, *, system_prompt=None, response_schema=None, keep_alive=None):
        self.calls.append(
            {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "response_schema": response_schema,
                "keep_alive": keep_alive,
            }
        )
        if not self.responses:
            return ""
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def _result(
    *,
    chunk_id: str,
    heading: str,
    text: str,
    distance: float,
    source_type: str = "report",
) -> RetrievalSearchResult:
    return RetrievalSearchResult(
        chunk_id=chunk_id,
        document_id=f"doc-{chunk_id}",
        source_type=source_type,
        source_id=f"source-{chunk_id}",
        document_title="고객 온보딩 회의록",
        chunk_text=text,
        chunk_heading=heading,
        distance=distance,
        session_id="session-1",
        report_id="report-1" if source_type == "report" else None,
    )


def _session(
    *,
    session_id: str,
    title: str,
    started_at: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=session_id,
        title=title,
        started_at=started_at,
        status=SimpleNamespace(value="ended"),
        primary_input_source="system_audio",
        participants=(),
    )


def test_assistant_chat_service가_retrieval_근거로_답변을_생성한다() -> None:
    retrieval = _FakeRetrievalQueryService(
        [
            _result(
                chunk_id="1",
                heading="결정 사항",
                text="온보딩 자료는 다음 주까지 공유하기로 했다.",
                distance=0.05,
            ),
            _result(
                chunk_id="2",
                heading="리스크",
                text="예산 확정이 늦어질 수 있다는 우려가 있었다.",
                distance=0.2,
            ),
        ]
    )
    completion = _FakeCompletionClient(
        [
            _plan_response("온보딩 자료 공유 결정"),
            "온보딩 자료 공유가 결정됐습니다. [S1]",
        ]
    )
    service = AssistantChatService(
        retrieval_query_service=retrieval,
        completion_client=completion,
        time_context_factory=_fixed_time_context,
    )

    result = service.answer(
        workspace_id="workspace-1",
        query="결정된 다음 할 일은?",
        source_types=("report",),
        session_id="session-1",
        limit=5,
    )

    assert result.answer == "온보딩 자료 공유가 결정됐습니다. [S1]"
    assert [item.chunk_id for item in result.sources] == ["1", "2"]
    assert retrieval.calls[0]["workspace_id"] == "workspace-1"
    assert retrieval.calls[0]["query"] == "온보딩 자료 공유 결정"
    assert retrieval.calls[0]["source_types"] == ("report",)
    assert retrieval.calls[0]["session_id"] == "session-1"
    assert completion.calls[0]["response_schema"] is not None
    assert "현재 사용자 시간: 2026-04-30 06:00:00 KST" in completion.calls[0]["prompt"]
    assert "결정 사항" in completion.calls[1]["prompt"]
    assert "해석된 시간 범위: 2026-04-30 06:00:00 KST 기준" in completion.calls[1]["prompt"]
    assert "제공된 회의 근거 안에서만 답변" in completion.calls[1]["system_prompt"]


def test_assistant_chat_service는_근거가_없으면_llm을_호출하지_않는다() -> None:
    retrieval = _FakeRetrievalQueryService([])
    completion = _FakeCompletionClient([_plan_response("없는 질문")])
    service = AssistantChatService(
        retrieval_query_service=retrieval,
        completion_client=completion,
        time_context_factory=_fixed_time_context,
    )

    result = service.answer(workspace_id="workspace-1", query="없는 질문")

    assert "관련 회의 근거를 찾지 못했습니다" in result.answer
    assert result.sources == []
    assert len(completion.calls) == 1
    assert completion.calls[0]["response_schema"] is not None


def test_assistant_chat_service는_noop_json이면_fallback_answer를_반환한다() -> None:
    retrieval = _FakeRetrievalQueryService(
        [
            _result(
                chunk_id="1",
                heading="회의내용",
                text="고객 응대 흐름을 단순화해야 한다는 의견이 있었다.",
                distance=0.1,
            )
        ]
    )
    completion = _FakeCompletionClient(
        [
            _plan_response("고객 응대 흐름 단순화"),
            '{"candidates": []}',
        ]
    )
    service = AssistantChatService(
        retrieval_query_service=retrieval,
        completion_client=completion,
        time_context_factory=_fixed_time_context,
    )

    result = service.answer(workspace_id="workspace-1", query="무슨 이야기를 했어?")

    assert "검색된 근거 기준" in result.answer
    assert "[S1]" in result.answer


def test_assistant_chat_service는_llm_실패시_근거_fallback을_반환한다() -> None:
    retrieval = _FakeRetrievalQueryService(
        [
            _result(
                chunk_id="1",
                heading="결정 사항",
                text="프로토타입 공유 일정을 금요일로 정했다.",
                distance=0.1,
            )
        ]
    )
    completion = _FakeCompletionClient(
        [
            _plan_response("프로토타입 공유 일정"),
            TimeoutError("LLM timeout"),
        ]
    )
    service = AssistantChatService(
        retrieval_query_service=retrieval,
        completion_client=completion,
        time_context_factory=_fixed_time_context,
    )

    result = service.answer(workspace_id="workspace-1", query="결정 사항 알려줘")

    assert "프로토타입 공유 일정" in result.answer
    assert result.sources[0].chunk_id == "1"


def test_assistant_chat_service는_계획_json이_깨져도_원질문으로_rag를_수행한다() -> None:
    retrieval = _FakeRetrievalQueryService(
        [
            _result(
                chunk_id="1",
                heading="회의내용",
                text="고객 응대 흐름을 단순화해야 한다는 의견이 있었다.",
                distance=0.1,
            )
        ]
    )
    completion = _FakeCompletionClient(["json 아님", "고객 응대 흐름 논의가 있었습니다. [S1]"])
    service = AssistantChatService(
        retrieval_query_service=retrieval,
        completion_client=completion,
        time_context_factory=_fixed_time_context,
    )

    result = service.answer(workspace_id="workspace-1", query="그 회의에서 뭐 얘기했어?")

    assert result.answer == "고객 응대 흐름 논의가 있었습니다. [S1]"
    assert retrieval.calls[0]["query"] == "그 회의에서 뭐 얘기했어?"


def test_assistant_chat_service는_세션_source_선택시_회의목록을_근거로_답한다() -> None:
    retrieval = _FakeRetrievalQueryService([])
    session_service = _FakeSessionService(
        [
            _session(
                session_id="session-1",
                title="test.wav 노트 생성 테스트",
                started_at="2026-04-04T02:15:00+00:00",
            ),
            _session(
                session_id="session-2",
                title="테스트",
                started_at="2026-04-04T01:55:00+00:00",
            ),
            _session(
                session_id="session-3",
                title="다른 날짜 회의",
                started_at="2026-04-05T07:06:00+00:00",
            ),
        ]
    )
    completion = _FakeCompletionClient(
        [
            _plan_response(
                "2026-04-04 회의 목록",
                retrieval_sources=["sessions"],
                target_dates=["2026-04-04"],
            ),
            "4월 4일 회의는 2건입니다: test.wav 노트 생성 테스트, 테스트. [S1]",
        ]
    )
    service = AssistantChatService(
        retrieval_query_service=retrieval,
        completion_client=completion,
        session_service=session_service,
        time_context_factory=_fixed_time_context,
    )

    result = service.answer(workspace_id="workspace-1", query="4월4일 회의 뭐있었지?")

    assert result.answer.startswith("4월 4일 회의는 2건")
    assert retrieval.calls == []
    assert session_service.calls[0]["limit"] == 50
    assert result.sources[0].source_type == "session"
    assert "test.wav 노트 생성 테스트" in result.sources[0].chunk_text
    assert "테스트" in result.sources[0].chunk_text
    assert "다른 날짜 회의" not in result.sources[0].chunk_text
    assert "source_type=session 근거" in completion.calls[1]["prompt"]
