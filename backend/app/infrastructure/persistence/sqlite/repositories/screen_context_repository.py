"""SQLite 화면 맥락 저장소 구현."""

from __future__ import annotations

from backend.app.domain.models.screen_context import ScreenContext
from backend.app.infrastructure.persistence.sqlite.database import Database
from backend.app.repositories.contracts.screen_context_repository import ScreenContextRepository


class SQLiteScreenContextRepository(ScreenContextRepository):
    """SQLite 기반 화면 맥락 저장소."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def save(self, screen_context: ScreenContext) -> ScreenContext:
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO screen_contexts (
                    id, session_id, captured_at_ms, ocr_text, title_hint, keywords_json, image_path
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    screen_context.id,
                    screen_context.session_id,
                    screen_context.captured_at_ms,
                    screen_context.ocr_text,
                    screen_context.title_hint,
                    screen_context.keywords_json,
                    screen_context.image_path,
                ),
            )
            connection.commit()
        return screen_context

    def list_by_session(self, session_id: str) -> list[ScreenContext]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM screen_contexts
                WHERE session_id = ?
                ORDER BY captured_at_ms ASC
                """,
                (session_id,),
            ).fetchall()
        return [
            ScreenContext(
                id=row["id"],
                session_id=row["session_id"],
                captured_at_ms=row["captured_at_ms"],
                ocr_text=row["ocr_text"],
                title_hint=row["title_hint"],
                keywords_json=row["keywords_json"],
                image_path=row["image_path"],
            )
            for row in rows
        ]
