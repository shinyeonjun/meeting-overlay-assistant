"""retrieval knowledge chunk 도메인 모델."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from server.app.core.identifiers import generate_uuid_str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class KnowledgeChunk:
    """벡터 검색 최소 단위 chunk."""

    id: str
    document_id: str
    chunk_index: int
    chunk_text: str
    embedding_model: str
    char_count: int
    token_count: int
    embedding: tuple[float, ...]
    chunk_heading: str | None = None
    created_at: str | None = None

    @classmethod
    def create(
        cls,
        *,
        document_id: str,
        chunk_index: int,
        chunk_text: str,
        embedding_model: str,
        embedding: list[float] | tuple[float, ...],
        chunk_heading: str | None = None,
        token_count: int | None = None,
    ) -> "KnowledgeChunk":
        """chunk 텍스트와 embedding으로 검색 단위를 생성한다."""

        normalized_embedding = tuple(float(value) for value in embedding)
        text = chunk_text.strip()
        return cls(
            id=generate_uuid_str(),
            document_id=document_id,
            chunk_index=chunk_index,
            chunk_text=text,
            embedding_model=embedding_model,
            char_count=len(text),
            token_count=token_count if token_count is not None else len(text.split()),
            embedding=normalized_embedding,
            chunk_heading=chunk_heading.strip() if chunk_heading else None,
            created_at=_utc_now_iso(),
        )
