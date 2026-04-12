"""화면 맥락 엔티티."""

from __future__ import annotations

from dataclasses import dataclass
from time import time
from uuid import uuid4


def _now_ms() -> int:
    return int(time() * 1000)


@dataclass(frozen=True)
class ScreenContext:
    """OCR 기반 화면 맥락 엔티티."""

    id: str
    session_id: str
    captured_at_ms: int
    ocr_text: str | None
    title_hint: str | None
    keywords_json: str | None = None
    image_path: str | None = None

    @classmethod
    def create(
        cls,
        session_id: str,
        ocr_text: str | None = None,
        title_hint: str | None = None,
        keywords_json: str | None = None,
        image_path: str | None = None,
    ) -> "ScreenContext":
        """새 화면 맥락을 생성한다."""
        return cls(
            id=f"screen-{uuid4().hex}",
            session_id=session_id,
            captured_at_ms=_now_ms(),
            ocr_text=ocr_text,
            title_hint=title_hint,
            keywords_json=keywords_json,
            image_path=image_path,
        )
