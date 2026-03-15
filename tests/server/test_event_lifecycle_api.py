"""이벤트 lifecycle API 테스트."""

from server.app.domain.models.meeting_event import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.domain.shared.enums import EventPriority, EventState, EventType
from server.app.infrastructure.persistence.sqlite.repositories.meeting_event_repository import (
    SQLiteMeetingEventRepository,
)
from server.app.infrastructure.persistence.sqlite.repositories.utterance_repository import (
    SQLiteUtteranceRepository,
)
from tests.fixtures.support.sample_inputs import SESSION_TITLE


class TestEventLifecycleApi:
    """상태 전이와 벌크 전이를 검증한다."""

    def test_question_event_can_transition_to_answered(self, client, isolated_database):
        session_id = _create_session(client)
        utterance_repository = SQLiteUtteranceRepository(isolated_database)
        event_id = _create_event(
            repository=SQLiteMeetingEventRepository(isolated_database),
            utterance_repository=utterance_repository,
            session_id=session_id,
            event_type=EventType.QUESTION,
            title="이 질문은 답변되었나요?",
            state=EventState.OPEN,
            priority=EventPriority.QUESTION,
        )

        response = client.post(
            f"/api/v1/sessions/{session_id}/events/{event_id}/transition",
            json={"target_state": "answered"},
        )

        assert response.status_code == 200
        assert response.json()["state"] == "answered"

    def test_question_event_invalid_transition_returns_400(self, client, isolated_database):
        session_id = _create_session(client)
        utterance_repository = SQLiteUtteranceRepository(isolated_database)
        event_id = _create_event(
            repository=SQLiteMeetingEventRepository(isolated_database),
            utterance_repository=utterance_repository,
            session_id=session_id,
            event_type=EventType.QUESTION,
            title="이 질문은 바로 확정될 수 없습니다.",
            state=EventState.OPEN,
            priority=EventPriority.QUESTION,
        )

        response = client.post(
            f"/api/v1/sessions/{session_id}/events/{event_id}/transition",
            json={"target_state": "confirmed"},
        )

        assert response.status_code == 400
        assert "허용되지 않는 상태 전이" in response.json()["detail"]

    def test_bulk_transition_closes_multiple_action_items(self, client, isolated_database):
        session_id = _create_session(client)
        repository = SQLiteMeetingEventRepository(isolated_database)
        utterance_repository = SQLiteUtteranceRepository(isolated_database)
        first_id = _create_event(
            repository=repository,
            utterance_repository=utterance_repository,
            session_id=session_id,
            event_type=EventType.ACTION_ITEM,
            title="민수가 일정 정리",
            state=EventState.OPEN,
            priority=EventPriority.ACTION_ITEM,
        )
        second_id = _create_event(
            repository=repository,
            utterance_repository=utterance_repository,
            session_id=session_id,
            event_type=EventType.ACTION_ITEM,
            title="영희가 QA 체크",
            state=EventState.OPEN,
            priority=EventPriority.ACTION_ITEM,
        )

        response = client.post(
            f"/api/v1/sessions/{session_id}/events/bulk-transition",
            json={
                "event_ids": [first_id, second_id],
                "target_state": "closed",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["updated_count"] == 2
        assert {item["state"] for item in payload["items"]} == {"closed"}


def _create_session(client) -> str:
    response = client.post(
        "/api/v1/sessions",
        json={
            "title": SESSION_TITLE,
            "mode": "meeting",
            "source": "system_audio",
        },
    )
    return response.json()["id"]


def _create_event(
    *,
    repository: SQLiteMeetingEventRepository,
    utterance_repository: SQLiteUtteranceRepository | None = None,
    session_id: str,
    event_type: EventType,
    title: str,
    state: EventState,
    priority: EventPriority,
) -> str:
    source_utterance_id = None
    if utterance_repository is not None:
        utterance = utterance_repository.save(
            Utterance.create(
                session_id=session_id,
                seq_num=1,
                start_ms=0,
                end_ms=1000,
                text=title,
                confidence=0.95,
            )
        )
        source_utterance_id = utterance.id

    event = repository.save(
        MeetingEvent.create(
            session_id=session_id,
            event_type=event_type,
            title=title,
            state=state,
            priority=priority,
            source_utterance_id=source_utterance_id,
            insight_scope="live",
        )
    )
    return event.id
