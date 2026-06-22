import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from server.app.domain.retrieval import RetrievalSearchResult
from server.app.services.assistant import AssistantChatService, AssistantTimeContext


def _fixed_time_context() -> AssistantTimeContext:
    return AssistantTimeContext(
        now=datetime(2026, 6, 10, 9, 0, 0, tzinfo=timezone(timedelta(hours=9))),
        timezone_name="Asia/Seoul",
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

    def list_sessions(self, **kwargs):
        return self.sessions


class _FakeCompletionClient:
    def __init__(self, responses):
        self.responses = list(responses)
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
        return self.responses.pop(0)


def _session(*, session_id: str, title: str, started_at: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=session_id,
        title=title,
        started_at=started_at,
        status=SimpleNamespace(value="ended"),
        primary_input_source="system_audio",
        participants=(),
    )


def _result(
    *,
    chunk_id: str,
    text: str,
    session_id: str,
    distance: float = 0.1,
) -> RetrievalSearchResult:
    return RetrievalSearchResult(
        chunk_id=chunk_id,
        document_id=f"doc-{chunk_id}",
        source_type="report",
        source_id=f"source-{chunk_id}",
        document_title=f"{session_id} report",
        chunk_text=text,
        chunk_heading="Decision",
        distance=distance,
        session_id=session_id,
    )


def _plan(
    *,
    session_scope: str,
    requires_knowledge: bool,
    content_focuses: list[str],
) -> str:
    return json.dumps(
        {
            "search_query": "latest meeting decision",
            "answer_focus": "resolved meeting answer",
            "retrieval_sources": ["sessions", "knowledge"],
            "target_dates": [],
            "time_scope": session_scope,
            "time_expression": "latest",
            "resolved_time_range": "",
            "session_scope": session_scope,
            "content_focuses": content_focuses,
            "requires_knowledge": requires_knowledge,
            "needs_clarification": False,
            "clarification_question": None,
            "confidence": 0.9,
        }
    )


def test_latest_meeting_metadata_uses_session_table_without_rag() -> None:
    retrieval = _FakeRetrievalQueryService(
        [_result(chunk_id="old", text="Old content", session_id="session-old")]
    )
    sessions = _FakeSessionService(
        [
            _session(
                session_id="session-old",
                title="Old meeting",
                started_at="2026-05-05T10:11:00+00:00",
            ),
            _session(
                session_id="session-new",
                title="Newest meeting",
                started_at="2026-06-09T08:38:00+00:00",
            ),
        ]
    )
    completion = _FakeCompletionClient(
        [
            _plan(session_scope="latest", requires_knowledge=False, content_focuses=["metadata"]),
            "가장 최근 회의는 Newest meeting입니다. [S1]",
        ]
    )
    service = AssistantChatService(
        retrieval_query_service=retrieval,
        completion_client=completion,
        session_service=sessions,
        time_context_factory=_fixed_time_context,
    )

    result = service.answer(workspace_id="workspace-1", query="가장 최근 회의가 뭐였지?")

    assert retrieval.calls == []
    assert [source.source_type for source in result.sources] == ["session"]
    assert "Newest meeting" in result.sources[0].chunk_text
    assert result.sources[0].metadata_json["knowledge_session_ids"] == []
    assert "Always answer in Korean" in completion.calls[1]["system_prompt"]


def test_latest_meeting_content_rag_is_scoped_to_resolved_session() -> None:
    retrieval = _FakeRetrievalQueryService(
        [
            _result(
                chunk_id="old-decision",
                text="Old meeting decision.",
                session_id="session-old",
                distance=0.01,
            ),
            _result(
                chunk_id="new-decision",
                text="Newest meeting decision.",
                session_id="session-new",
                distance=0.2,
            ),
        ]
    )
    sessions = _FakeSessionService(
        [
            _session(
                session_id="session-old",
                title="Old meeting",
                started_at="2026-05-05T10:11:00+00:00",
            ),
            _session(
                session_id="session-new",
                title="Newest meeting",
                started_at="2026-06-09T08:38:00+00:00",
            ),
        ]
    )
    completion = _FakeCompletionClient(
        [
            _plan(session_scope="latest", requires_knowledge=True, content_focuses=["decision"]),
            "지난 회의 결정은 Newest meeting decision입니다. [S2]",
        ]
    )
    service = AssistantChatService(
        retrieval_query_service=retrieval,
        completion_client=completion,
        session_service=sessions,
        time_context_factory=_fixed_time_context,
    )

    result = service.answer(workspace_id="workspace-1", query="지난 회의에서 결정된 건 뭐야?")

    assert retrieval.calls[0]["session_ids"] == ("session-new",)
    assert [source.chunk_id for source in result.sources] == [
        "session-lookup:recent",
        "new-decision",
    ]
    assert all(source.session_id != "session-old" for source in result.sources[1:])
