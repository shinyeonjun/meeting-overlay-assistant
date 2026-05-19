"""회의록 문서 생성에 필요한 세션 메타데이터 context."""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class ReportSessionContext:
    """회의록 템플릿에 매핑할 세션 메타데이터."""

    session_id: str
    title: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    participants: tuple[str, ...] = ()
    organizer: str | None = None
    primary_input_source: str | None = None
    actual_active_sources: tuple[str, ...] = ()
    recording_file_modified_at: str | None = None
    recording_duration_ms: int | None = None

    @classmethod
    def from_session(cls, session) -> "ReportSessionContext":
        """MeetingSession 또는 동일 속성을 가진 객체에서 context를 만든다."""

        return cls(
            session_id=str(getattr(session, "id", "")),
            title=getattr(session, "title", None),
            started_at=getattr(session, "started_at", None),
            ended_at=getattr(session, "ended_at", None),
            participants=tuple(getattr(session, "participants", ()) or ()),
            organizer=(
                getattr(session, "organizer", None)
                or getattr(session, "host", None)
                or getattr(session, "created_by", None)
            ),
            primary_input_source=getattr(session, "primary_input_source", None),
            actual_active_sources=tuple(
                getattr(session, "actual_active_sources", ()) or ()
            ),
        )

    def with_recording_metadata(
        self,
        *,
        recording_file_modified_at: str | None,
        recording_duration_ms: int | None,
    ) -> "ReportSessionContext":
        return replace(
            self,
            recording_file_modified_at=recording_file_modified_at,
            recording_duration_ms=recording_duration_ms,
        )
