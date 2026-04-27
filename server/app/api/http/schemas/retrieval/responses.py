"""retrieval 응답 스키마."""

from pydantic import BaseModel


class RetrievalSearchItemResponse(BaseModel):
    """retrieval 검색 결과 1건."""

    chunk_id: str
    document_id: str
    source_type: str
    source_id: str
    document_title: str
    chunk_text: str
    chunk_heading: str | None = None
    distance: float
    source_ref: str | None = None
    speaker_label: str | None = None
    start_ms: int | None = None
    end_ms: int | None = None
    metadata_json: dict[str, object] | None = None
    session_id: str | None = None
    report_id: str | None = None
    account_id: str | None = None
    contact_id: str | None = None
    context_thread_id: str | None = None


class RetrievalSearchResponse(BaseModel):
    """retrieval 검색 응답."""

    query: str
    limit: int
    result_count: int
    items: list[RetrievalSearchItemResponse]
