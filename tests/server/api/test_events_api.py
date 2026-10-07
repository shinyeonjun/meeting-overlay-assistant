"""이벤트 관리 API 테스트."""

from server.app.domain.models.meeting_event import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.domain.shared.enums import EventState, EventType
from server.app.infrastructure.persistence.postgresql.repositories.events import (
    PostgreSQLMeetingEventRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_utterance_repository import (
    PostgreSQLUtteranceRepository,
)
from tests.fixtures.support.sample_inputs import (
    DECISION_TEXT,
    QUESTION_TEXT,
    SESSION_TITLE,
)


class TestEventsApi:
    """이벤트 조회, 수정, 삭제 API를 검증한다.

    text WebSocket 경로는 live runtime 데이터를 DB에 저장하지 않으므로
    (persist_live_runtime_data=False), 이벤트는 repository로 직접 시드한다.
    """

    def test_세션_이벤트_목록을_조회할_수_있다(self, client, isolated_database):
        session_id = _create_session(client)
        _seed_events(
            isolated_database,
            session_id,
            [(QUESTION_TEXT, EventType.QUESTION, EventState.OPEN)],
        )

        response = client.get(f"/api/v1/sessions/{session_id}/events")

        assert response.status_code == 200
        payload = response.json()
        assert len(payload["items"]) == 1
        assert {item["event_type"] for item in payload["items"]} == {"question"}
        assert {item["source_utterance_id"] for item in payload["items"]} != {None}

    def test_타입과_상태로_이벤트를_필터링할_수_있다(self, client, isolated_database):
        session_id = _create_session(client)
        _seed_events(
            isolated_database,
            session_id,
            [
                (QUESTION_TEXT, EventType.QUESTION, EventState.OPEN),
                (DECISION_TEXT, EventType.DECISION, EventState.CONFIRMED),
            ],
        )

        response = client.get(
            f"/api/v1/sessions/{session_id}/events",
            params={"event_type": "question", "state": "open"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert len(payload["items"]) == 1
        assert payload["items"][0]["event_type"] == "question"
        assert payload["items"][0]["state"] == "open"

    def test_이벤트를_patch로_수정할_수_있다(self, client, isolated_database):
        session_id = _create_session(client)
        _seed_events(
            isolated_database,
            session_id,
            [(QUESTION_TEXT, EventType.QUESTION, EventState.OPEN)],
        )

        list_response = client.get(f"/api/v1/sessions/{session_id}/events")
        event_id = list_response.json()["items"][0]["id"]

        response = client.patch(
            f"/api/v1/sessions/{session_id}/events/{event_id}",
            json={
                "title": "사파리에서만 재현되는지 다시 확인이 필요합니다.",
                "state": "answered",
                "evidence_text": "사파리에서만 재현되는지 다시 확인해 주세요.",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["title"] == "사파리에서만 재현되는지 다시 확인이 필요합니다."
        assert payload["state"] == "answered"
        assert payload["evidence_text"] == "사파리에서만 재현되는지 다시 확인해 주세요."

    def test_이벤트_타입을_바꿀_수_있다(self, client, isolated_database):
        session_id = _create_session(client)
        _seed_events(
            isolated_database,
            session_id,
            [(QUESTION_TEXT, EventType.QUESTION, EventState.OPEN)],
        )

        list_response = client.get(f"/api/v1/sessions/{session_id}/events")
        event_id = list_response.json()["items"][0]["id"]

        response = client.patch(
            f"/api/v1/sessions/{session_id}/events/{event_id}",
            json={"event_type": "risk"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["event_type"] == "risk"
        assert payload["state"] == "open"

    def test_이벤트를_삭제할_수_있다(self, client, isolated_database):
        session_id = _create_session(client)
        _seed_events(
            isolated_database,
            session_id,
            [(QUESTION_TEXT, EventType.QUESTION, EventState.OPEN)],
        )

        list_response = client.get(f"/api/v1/sessions/{session_id}/events")
        event_id = list_response.json()["items"][0]["id"]

        delete_response = client.delete(f"/api/v1/sessions/{session_id}/events/{event_id}")
        assert delete_response.status_code == 204

        second_list_response = client.get(f"/api/v1/sessions/{session_id}/events")
        assert second_list_response.status_code == 200
        assert second_list_response.json()["items"] == []


def _create_session(client) -> str:
    response = client.post(
        "/api/v1/sessions",
        json={
            "title": SESSION_TITLE,
            "mode": "meeting",
            "source": "system_audio",
        },
    )
    session_id = response.json()["id"]
    start_response = client.post(f"/api/v1/sessions/{session_id}/start")
    assert start_response.status_code == 200
    return session_id


def _seed_events(
    isolated_database,
    session_id: str,
    items: list[tuple[str, EventType, EventState]],
) -> None:
    utterance_repository = PostgreSQLUtteranceRepository(isolated_database)
    event_repository = PostgreSQLMeetingEventRepository(isolated_database)

    for index, (text, event_type, state) in enumerate(items, start=1):
        utterance = utterance_repository.save(
            Utterance.create(
                session_id=session_id,
                seq_num=index,
                start_ms=(index - 1) * 1000,
                end_ms=index * 1000,
                text=text,
                confidence=0.95,
                input_source="system_audio",
            )
        )
        event_repository.save(
            MeetingEvent.create(
                session_id=session_id,
                event_type=event_type,
                title=text,
                state=state,
                source_utterance_id=utterance.id,
                evidence_text=text,
                input_source="system_audio",
            )
        )
