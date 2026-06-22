"""PostgreSQL assistant conversation repository."""

from __future__ import annotations

from server.app.domain.models.assistant_conversation import (
    AssistantConversation,
    AssistantMessage,
)
from server.app.infrastructure.persistence.postgresql.repositories._base import (
    PostgreSQLRepositoryBase,
    parse_json_value,
)
from server.app.infrastructure.persistence.postgresql.repositories.retrieval.jsonb import (
    dump_jsonb,
)
from server.app.repositories.contracts.assistant_conversation_repository import (
    AssistantConversationRepository,
)


class PostgreSQLAssistantConversationRepository(
    PostgreSQLRepositoryBase,
    AssistantConversationRepository,
):
    """Store assistant conversations and messages in PostgreSQL."""

    def get_conversation(
        self,
        *,
        conversation_id: str,
        workspace_id: str,
    ) -> AssistantConversation | None:
        with self._database.transaction() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM assistant_conversations
                WHERE id = %s AND workspace_id = %s
                """,
                (conversation_id, workspace_id),
            ).fetchone()
        return self._to_conversation(row) if row is not None else None

    def list_conversations(
        self,
        *,
        workspace_id: str,
        user_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
        limit: int = 30,
    ) -> list[AssistantConversation]:
        normalized_limit = max(1, min(int(limit), 100))
        filters = ["workspace_id = %s"]
        params: list[object] = [workspace_id]
        optional_filters = (
            ("user_id", user_id),
            ("account_id", account_id),
            ("contact_id", contact_id),
            ("context_thread_id", context_thread_id),
        )
        for column_name, value in optional_filters:
            if value is None:
                continue
            filters.append(f"{column_name} = %s")
            params.append(value)
        params.append(normalized_limit)

        with self._database.transaction() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM assistant_conversations
                WHERE {' AND '.join(filters)}
                ORDER BY updated_at DESC, created_at DESC, id DESC
                LIMIT %s
                """,
                tuple(params),
            ).fetchall()
        return [self._to_conversation(row) for row in rows]

    def delete_conversation(
        self,
        *,
        conversation_id: str,
        workspace_id: str,
    ) -> bool:
        with self._database.transaction() as connection:
            row = connection.execute(
                """
                DELETE FROM assistant_conversations
                WHERE id = %s AND workspace_id = %s
                RETURNING id
                """,
                (conversation_id, workspace_id),
            ).fetchone()
        return row is not None

    def upsert_conversation(
        self,
        conversation: AssistantConversation,
    ) -> AssistantConversation:
        with self._database.transaction() as connection:
            row = connection.execute(
                """
                INSERT INTO assistant_conversations (
                    id,
                    workspace_id,
                    user_id,
                    account_id,
                    contact_id,
                    context_thread_id,
                    title,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    workspace_id = EXCLUDED.workspace_id,
                    user_id = EXCLUDED.user_id,
                    account_id = EXCLUDED.account_id,
                    contact_id = EXCLUDED.contact_id,
                    context_thread_id = EXCLUDED.context_thread_id,
                    title = COALESCE(NULLIF(assistant_conversations.title, ''), EXCLUDED.title),
                    status = EXCLUDED.status,
                    updated_at = EXCLUDED.updated_at
                RETURNING *
                """,
                (
                    conversation.id,
                    conversation.workspace_id,
                    conversation.user_id,
                    conversation.account_id,
                    conversation.contact_id,
                    conversation.context_thread_id,
                    conversation.title,
                    conversation.status,
                    conversation.created_at,
                    conversation.updated_at,
                ),
            ).fetchone()
        return self._to_conversation(row)

    def list_messages(
        self,
        *,
        conversation_id: str,
        workspace_id: str,
        limit: int = 40,
        statuses: tuple[str, ...] = (),
    ) -> list[AssistantMessage]:
        normalized_limit = max(1, min(int(limit), 100))
        params: list[object] = [conversation_id, workspace_id]
        status_filter = ""
        if statuses:
            placeholders = ", ".join(["%s"] * len(statuses))
            status_filter = f" AND messages.status IN ({placeholders})"
            params.extend(statuses)
        params.append(normalized_limit)

        with self._database.transaction() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM (
                    SELECT messages.*
                    FROM assistant_messages AS messages
                    INNER JOIN assistant_conversations AS conversations
                        ON conversations.id = messages.conversation_id
                    WHERE messages.conversation_id = %s
                      AND conversations.workspace_id = %s
                      {status_filter}
                    ORDER BY messages.created_at DESC, messages.id DESC
                    LIMIT %s
                ) AS recent_messages
                ORDER BY recent_messages.created_at ASC, recent_messages.id ASC
                """,
                tuple(params),
            ).fetchall()
        return [self._to_message(row) for row in rows]

    def append_message(self, message: AssistantMessage) -> AssistantMessage:
        with self._database.transaction() as connection:
            row = connection.execute(
                """
                INSERT INTO assistant_messages (
                    id,
                    conversation_id,
                    role,
                    content,
                    status,
                    error_message,
                    sources_json,
                    metadata_json,
                    created_at,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
                RETURNING *
                """,
                (
                    message.id,
                    message.conversation_id,
                    message.role,
                    message.content,
                    message.status,
                    message.error_message,
                    dump_jsonb(message.sources_json or []),
                    dump_jsonb(message.metadata_json or {}),
                    message.created_at,
                    message.updated_at,
                ),
            ).fetchone()
            connection.execute(
                """
                UPDATE assistant_conversations
                SET updated_at = %s
                WHERE id = %s
                """,
                (message.updated_at, message.conversation_id),
            )
        return self._to_message(row)

    def update_message(
        self,
        *,
        message_id: str,
        content: str,
        status: str,
        error_message: str | None = None,
        sources_json: list[dict] | None = None,
        metadata_json: dict | None = None,
    ) -> AssistantMessage | None:
        with self._database.transaction() as connection:
            row = connection.execute(
                """
                UPDATE assistant_messages
                SET content = %s,
                    status = %s,
                    error_message = %s,
                    sources_json = %s::jsonb,
                    metadata_json = %s::jsonb,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING *
                """,
                (
                    content,
                    status,
                    error_message,
                    dump_jsonb(sources_json or []),
                    dump_jsonb(metadata_json or {}),
                    message_id,
                ),
            ).fetchone()
            if row is not None:
                connection.execute(
                    """
                    UPDATE assistant_conversations
                    SET updated_at = %s
                    WHERE id = %s
                    """,
                    (row["updated_at"], row["conversation_id"]),
                )
        return self._to_message(row) if row is not None else None

    @staticmethod
    def _to_conversation(row) -> AssistantConversation:
        return AssistantConversation(
            id=row["id"],
            workspace_id=row["workspace_id"],
            user_id=row["user_id"],
            account_id=row["account_id"],
            contact_id=row["contact_id"],
            context_thread_id=row["context_thread_id"],
            title=row["title"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _to_message(row) -> AssistantMessage:
        sources = parse_json_value(row["sources_json"], default=[])
        metadata = parse_json_value(row["metadata_json"], default={})
        return AssistantMessage(
            id=row["id"],
            conversation_id=row["conversation_id"],
            role=row["role"],
            content=row["content"],
            status=row["status"],
            error_message=row["error_message"],
            sources_json=sources if isinstance(sources, list) else [],
            metadata_json=metadata if isinstance(metadata, dict) else {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
