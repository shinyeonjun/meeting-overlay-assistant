"""회의록 생성 가능한 세션 fixture helper."""

from __future__ import annotations

from server.app.domain.events.meeting_event import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.domain.shared.enums import EventState, EventType
from server.app.infrastructure.persistence.postgresql.repositories.events import (
    PostgreSQLMeetingEventRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_utterance_repository import (
    PostgreSQLUtteranceRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.session import (
    PostgreSQLSessionRepository,
)
from tests.fixtures.support.sample_inputs import DECISION_TEXT


def prepare_report_ready_session(
    *,
    client,
    isolated_database,
    session_id: str,
    headers: dict[str, str] | None = None,
    text: str = DECISION_TEXT,
) -> None:
    """세션을 종료하고 canonical transcript/event를 심어 회의록 생성 가능 상태로 만든다."""

    request_headers = headers or {}
    end_response = client.post(
        f"/api/v1/sessions/{session_id}/end",
        headers=request_headers,
    )
    assert end_response.status_code == 200
    _seed_canonical_decision(isolated_database, session_id, text=text)
    _mark_post_processing_completed(isolated_database, session_id)


def _seed_canonical_decision(
    isolated_database,
    session_id: str,
    *,
    text: str,
) -> None:
    utterance_repository = PostgreSQLUtteranceRepository(isolated_database)
    event_repository = PostgreSQLMeetingEventRepository(isolated_database)

    utterance = utterance_repository.save(
        Utterance.create(
            session_id=session_id,
            seq_num=1,
            start_ms=0,
            end_ms=1000,
            text=text,
            confidence=0.95,
            speaker_label="SPEAKER_00",
            transcript_source="post_processed",
        )
    )
    event_repository.save(
        MeetingEvent.create(
            session_id=session_id,
            event_type=EventType.DECISION,
            title=text,
            state=EventState.CONFIRMED,
            source_utterance_id=utterance.id,
            evidence_text=utterance.text,
            speaker_label=utterance.speaker_label,
            input_source=utterance.input_source,
            insight_scope="finalized",
            event_source="post_processed",
            finalized_at_ms=1,
        )
    )


def _mark_post_processing_completed(isolated_database, session_id: str) -> None:
    session_repository = PostgreSQLSessionRepository(isolated_database)
    session = session_repository.get_by_id(session_id)
    assert session is not None
    session_repository.save(session.mark_post_processing_completed())
