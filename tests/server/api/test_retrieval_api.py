"""retrieval API 테스트."""

from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_ID
from server.app.api.http.routes.retrieval import query as retrieval_query_routes
from server.app.domain.retrieval import RetrievalSearchResult


class _FakeRetrievalQueryService:
    def search(
        self,
        *,
        workspace_id: str,
        query: str,
        source_types: tuple[str, ...] = (),
        session_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
        limit: int = 10,
    ) -> list[RetrievalSearchResult]:
        assert workspace_id == DEFAULT_WORKSPACE_ID
        assert query == "합성"
        assert source_types == ("report", "note")
        assert session_id == "session-1"
        assert limit == 3
        return [
            RetrievalSearchResult(
                chunk_id="chunk-1",
                document_id="doc-1",
                source_type="report",
                source_id="report-1",
                document_title="합성 결제 회의록 v1",
                chunk_text="합성 결제 라우팅 수정안 정리 요청",
                chunk_heading="액션 아이템",
                distance=0.12,
                source_ref="utt-1",
                speaker_label="SPEAKER_00",
                start_ms=1200,
                end_ms=3400,
                metadata_json={"event_type": "action_item"},
                session_id="session-1",
                report_id="report-1",
                account_id="account-1",
                contact_id="contact-1",
                context_thread_id="thread-1",
            )
        ]


def test_retrieval_search_api가_검색_결과를_반환한다(client, monkeypatch) -> None:
    monkeypatch.setattr(
        retrieval_query_routes,
        "get_retrieval_query_service",
        lambda: _FakeRetrievalQueryService(),
    )

    response = client.get(
        "/api/v1/retrieval/search",
        params={
            "q": "합성",
            "source_type": ["report", "note"],
            "session_id": "session-1",
            "limit": 3,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "합성"
    assert payload["result_count"] == 1
    assert payload["items"][0]["document_id"] == "doc-1"
    assert payload["items"][0]["chunk_heading"] == "액션 아이템"
    assert payload["items"][0]["source_ref"] == "utt-1"
    assert payload["items"][0]["speaker_label"] == "SPEAKER_00"
    assert payload["items"][0]["metadata_json"]["event_type"] == "action_item"
