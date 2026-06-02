"""assistant RAG context ranker 테스트."""

from server.app.domain.retrieval import RetrievalSearchResult
from server.app.services.assistant.chat.retrieval.context_ranker import (
    select_context_sources,
)


def _result(
    *,
    chunk_id: str,
    heading: str,
    text: str,
    distance: float,
    section_role: str,
    source_type: str = "report",
    document_id: str | None = None,
    rank_score: float | None = None,
    metadata_json: dict[str, object] | None = None,
) -> RetrievalSearchResult:
    metadata = {"section_role": section_role}
    if metadata_json:
        metadata.update(metadata_json)
    return RetrievalSearchResult(
        chunk_id=chunk_id,
        document_id=document_id or f"doc-{chunk_id}",
        source_type=source_type,
        source_id=f"source-{chunk_id}",
        document_title="고객 회의록",
        chunk_text=text,
        chunk_heading=heading,
        distance=distance,
        rank_score=rank_score,
        metadata_json=metadata,
    )


def test_context_ranker는_질문_의도와_맞는_섹션을_우선한다() -> None:
    candidates = [
        _result(
            chunk_id="summary",
            heading="요약",
            text="전체 회의 요약입니다.",
            distance=0.05,
            section_role="summary",
        ),
        _result(
            chunk_id="action",
            heading="다음 할 일",
            text="민수가 QA 체크리스트를 갱신한다.",
            distance=0.15,
            section_role="action_item",
        ),
    ]

    selected = select_context_sources(
        query="해야 할 일 알려줘",
        search_query="해야 할 일",
        candidates=candidates,
        limit=2,
    )

    assert [item.chunk_id for item in selected] == ["action", "summary"]


def test_context_ranker_prioritizes_document_sources_for_document_queries() -> None:
    candidates = [
        _result(
            chunk_id="report",
            heading="Decision",
            text="The team discussed the budget.",
            distance=0.05,
            section_role="decision",
            source_type="report",
        ),
        _result(
            chunk_id="document",
            heading="Budget file",
            text="The budget cap is 10 million KRW.",
            distance=0.11,
            section_role="discussion",
            source_type="document",
            metadata_json={"source_kind": "document"},
        ),
    ]

    selected = select_context_sources(
        query="Find the budget in the document file",
        search_query="budget document file",
        candidates=candidates,
        limit=2,
    )

    assert [item.chunk_id for item in selected] == ["document", "report"]


def test_context_ranker는_비슷한_chunk가_프롬프트를_독점하지_않게_분산한다() -> None:
    candidates = [
        _result(
            chunk_id="same-1",
            document_id="doc-a",
            heading="회의 내용",
            text="결제 라우팅 정책을 금요일까지 확정한다.",
            distance=0.01,
            section_role="discussion",
        ),
        _result(
            chunk_id="same-2",
            document_id="doc-a",
            heading="회의 내용",
            text="결제 라우팅 정책을 금요일까지 확정한다는 이야기가 있었다.",
            distance=0.02,
            section_role="discussion",
        ),
        _result(
            chunk_id="other",
            document_id="doc-b",
            heading="결정 사항",
            text="정산 검증 방식은 다음 회의에서 다시 확인한다.",
            distance=0.08,
            section_role="decision",
        ),
    ]

    selected = select_context_sources(
        query="결제 라우팅 알려줘",
        search_query="결제 라우팅",
        candidates=candidates,
        limit=2,
    )

    assert [item.chunk_id for item in selected] == ["same-1", "other"]


def test_context_ranker_uses_hybrid_rank_score_before_raw_distance() -> None:
    candidates = [
        _result(
            chunk_id="semantic-only",
            heading="Discussion",
            text="The team mentioned a loosely related topic.",
            distance=0.02,
            rank_score=0.02,
            section_role="discussion",
        ),
        _result(
            chunk_id="hybrid-match",
            heading="Action items",
            text="The exact keyword matched the user question and the vector candidate.",
            distance=0.18,
            rank_score=0.04,
            section_role="discussion",
        ),
    ]

    selected = select_context_sources(
        query="exact keyword",
        search_query="exact keyword",
        candidates=candidates,
        limit=2,
    )

    assert [item.chunk_id for item in selected] == ["hybrid-match", "semantic-only"]
