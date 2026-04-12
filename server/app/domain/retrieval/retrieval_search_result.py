"""retrieval 검색 결과 도메인 모델."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalSearchResult:
    """hybrid retrieval 검색 결과 1건."""

    chunk_id: str
    document_id: str
    source_type: str
    source_id: str
    document_title: str
    chunk_text: str
    chunk_heading: str | None
    distance: float
    session_id: str | None = None
    report_id: str | None = None
    account_id: str | None = None
    contact_id: str | None = None
    context_thread_id: str | None = None
