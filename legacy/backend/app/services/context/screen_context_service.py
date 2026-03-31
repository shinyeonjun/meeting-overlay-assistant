"""화면 맥락 서비스."""

from __future__ import annotations

from backend.app.domain.models.screen_context import ScreenContext
from backend.app.repositories.contracts.screen_context_repository import ScreenContextRepository


class ScreenContextService:
    """화면 OCR 결과와 제목 힌트를 저장한다."""

    def __init__(self, screen_context_repository: ScreenContextRepository) -> None:
        self._screen_context_repository = screen_context_repository

    def save_context(
        self,
        session_id: str,
        ocr_text: str | None = None,
        title_hint: str | None = None,
        keywords_json: str | None = None,
        image_path: str | None = None,
    ) -> ScreenContext:
        """화면 맥락을 저장한다."""
        screen_context = ScreenContext.create(
            session_id=session_id,
            ocr_text=ocr_text,
            title_hint=title_hint,
            keywords_json=keywords_json,
            image_path=image_path,
        )
        return self._screen_context_repository.save(screen_context)
