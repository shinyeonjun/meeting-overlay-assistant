"""retrieval knowledge 문서 도메인 모델."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from server.app.core.identifiers import generate_uuid_str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class KnowledgeDocument:
    """retrieval / memory 계층에 적재되는 문서 단위 정본."""

    id: str
    workspace_id: str
    source_type: str
    source_id: str
    title: str
    body: str
    content_hash: str
    session_id: str | None = None
    report_id: str | None = None
    account_id: str | None = None
    contact_id: str | None = None
    context_thread_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    indexed_at: str | None = None

    @classmethod
    def create(
        cls,
        *,
        workspace_id: str,
        source_type: str,
        source_id: str,
        title: str,
        body: str,
        content_hash: str,
        session_id: str | None = None,
        report_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
        existing_id: str | None = None,
        created_at: str | None = None,
    ) -> "KnowledgeDocument":
        """문서를 새로 만들거나 기존 문서를 갱신 가능한 형태로 생성한다."""

        now = _utc_now_iso()
        return cls(
            id=existing_id or generate_uuid_str(),
            workspace_id=workspace_id,
            source_type=source_type,
            source_id=source_id,
            title=title,
            body=body,
            content_hash=content_hash,
            session_id=session_id,
            report_id=report_id,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
            created_at=created_at or now,
            updated_at=now,
            indexed_at=now,
        )
