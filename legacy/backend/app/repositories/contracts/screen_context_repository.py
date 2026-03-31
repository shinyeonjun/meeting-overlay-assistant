"""화면 맥락 저장소 인터페이스."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.app.domain.models.screen_context import ScreenContext


class ScreenContextRepository(ABC):
    """화면 맥락 저장소 인터페이스."""

    @abstractmethod
    def save(self, screen_context: ScreenContext) -> ScreenContext:
        raise NotImplementedError

    @abstractmethod
    def list_by_session(self, session_id: str) -> list[ScreenContext]:
        raise NotImplementedError
