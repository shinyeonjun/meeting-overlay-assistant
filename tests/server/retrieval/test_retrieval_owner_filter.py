"""검색은 요청 사용자가 만든 회의의 자료만 돌려준다 (DB 포함 검증)."""

from __future__ import annotations

from server.app.domain.retrieval import KnowledgeChunk, KnowledgeDocument
from server.app.domain.shared.enums import AudioSource, SessionMode
from server.app.infrastructure.persistence.postgresql.repositories.retrieval import (
    PostgreSQLKnowledgeChunkRepository,
    PostgreSQLKnowledgeDocumentRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.session import (
    PostgreSQLSessionRepository,
)
from server.app.services.sessions.session_service import SessionService

WORKSPACE_ID = "workspace-default"
EMBEDDING = [0.1] * 768
EMBEDDING_MODEL = "test-embedding"


def _insert_user(isolated_database, user_id: str) -> None:
    with isolated_database.transaction() as connection:
        connection.execute(
            """
            INSERT INTO users (id, login_id, display_name, created_at, updated_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO NOTHING
            """,
            (user_id, f"{user_id}@test.local", user_id),
        )


def _create_indexed_session(isolated_database, *, owner_id: str, title: str, text: str) -> str:
    session_service = SessionService(PostgreSQLSessionRepository(isolated_database))
    session = session_service.create_session_draft(
        title=title,
        mode=SessionMode.MEETING,
        source=AudioSource.SYSTEM_AUDIO,
        created_by_user_id=owner_id,
    )
    document_repository = PostgreSQLKnowledgeDocumentRepository(isolated_database)
    chunk_repository = PostgreSQLKnowledgeChunkRepository(isolated_database)
    document = document_repository.upsert(
        KnowledgeDocument.create(
            workspace_id=WORKSPACE_ID,
            source_type="report",
            source_id=f"report-{session.id}",
            title=title,
            body=text,
            content_hash=f"hash-{session.id}",
            session_id=session.id,
        )
    )
    chunk_repository.replace_for_document(
        document_id=document.id,
        chunks=[
            KnowledgeChunk.create(
                document_id=document.id,
                chunk_index=0,
                chunk_text=text,
                embedding_model=EMBEDDING_MODEL,
                embedding=EMBEDDING,
                chunk_heading=title,
            )
        ],
    )
    return session.id


def _search(isolated_database, *, owner_user_id: str | None) -> set[str]:
    results = PostgreSQLKnowledgeChunkRepository(isolated_database).search_hybrid(
        workspace_id=WORKSPACE_ID,
        query_text="예산",
        query_embedding=EMBEDDING,
        owner_user_id=owner_user_id,
        limit=10,
    )
    return {item.document_title for item in results}


def test_owner_필터가_있으면_본인이_만든_회의의_자료만_검색된다(isolated_database):
    _insert_user(isolated_database, "user-a")
    _insert_user(isolated_database, "user-b")
    _create_indexed_session(
        isolated_database, owner_id="user-a", title="A의 예산 회의", text="예산 계획을 논의했다"
    )
    _create_indexed_session(
        isolated_database, owner_id="user-b", title="B의 예산 회의", text="예산 집행을 검토했다"
    )

    found = _search(isolated_database, owner_user_id="user-a")

    assert found == {"A의 예산 회의"}


def test_owner_필터가_없으면_워크스페이스_전체가_검색된다(isolated_database):
    _insert_user(isolated_database, "user-a")
    _insert_user(isolated_database, "user-b")
    _create_indexed_session(
        isolated_database, owner_id="user-a", title="A의 예산 회의", text="예산 계획을 논의했다"
    )
    _create_indexed_session(
        isolated_database, owner_id="user-b", title="B의 예산 회의", text="예산 집행을 검토했다"
    )

    found = _search(isolated_database, owner_user_id=None)

    assert found == {"A의 예산 회의", "B의 예산 회의"}


def test_owner_필터는_세션이_없는_문서를_제외한다(isolated_database):
    document_repository = PostgreSQLKnowledgeDocumentRepository(isolated_database)
    chunk_repository = PostgreSQLKnowledgeChunkRepository(isolated_database)
    document = document_repository.upsert(
        KnowledgeDocument.create(
            workspace_id=WORKSPACE_ID,
            source_type="history_carry_over",
            source_id="carry-over-1",
            title="세션 없는 예산 메모",
            body="예산 메모",
            content_hash="hash-carry-over",
        )
    )
    chunk_repository.replace_for_document(
        document_id=document.id,
        chunks=[
            KnowledgeChunk.create(
                document_id=document.id,
                chunk_index=0,
                chunk_text="예산 메모",
                embedding_model=EMBEDDING_MODEL,
                embedding=EMBEDDING,
            )
        ],
    )

    assert "세션 없는 예산 메모" in _search(isolated_database, owner_user_id=None)
    assert _search(isolated_database, owner_user_id="user-a") == set()
