"""세션 엔티티."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from uuid import uuid4

from backend.app.domain.shared.enums import AudioSource, SessionMode, SessionStatus


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class MeetingSession:
    """회의 세션 엔티티."""

    id: str
    title: str
    mode: SessionMode
    source: AudioSource
    status: SessionStatus
    started_at: str
    ended_at: str | None = None
    primary_input_source: str | None = None
    actual_active_sources: tuple[str, ...] = ()

    @classmethod
    def start(cls, title: str, mode: SessionMode, source: AudioSource) -> "MeetingSession":
        """새 세션을 시작한다."""
        return cls(
            id=f"session-{uuid4().hex}",
            title=title,
            mode=mode,
            source=source,
            status=SessionStatus.RUNNING,
            started_at=_utc_now_iso(),
            primary_input_source=source.value,
            actual_active_sources=(),
        )

    def end(self) -> "MeetingSession":
        """세션을 종료 상태로 전환한다."""
        return replace(self, status=SessionStatus.ENDED, ended_at=_utc_now_iso())

    def mark_active_source(self, input_source: str) -> "MeetingSession":
        """실제로 감지된 입력 소스를 세션에 기록한다."""
        normalized = input_source.strip()
        if not normalized:
            return self
        if normalized in self.actual_active_sources:
            return self
        return replace(self, actual_active_sources=(*self.actual_active_sources, normalized))
