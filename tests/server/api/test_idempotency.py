"""같은 요청을 다시 보내도 결과가 같아야 하는 조작들의 멱등성 검증."""

from __future__ import annotations


from server.app.domain.shared.enums import EventPriority, EventState, EventType
from server.app.infrastructure.persistence.postgresql.repositories.events.postgresql_event_repository import (
    PostgreSQLMeetingEventRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_utterance_repository import (
    PostgreSQLUtteranceRepository,
)
from tests.server.api.test_event_lifecycle_api import _create_event, _create_session


def _create_started_session(client) -> str:
    session_id = _create_session(client)
    assert client.post(f"/api/v1/sessions/{session_id}/start").status_code == 200
    return session_id


def test_세션_시작을_두_번_해도_시작_시각과_상태가_바뀌지_않는다(client):
    session_id = _create_started_session(client)
    first = client.get(f"/api/v1/sessions/{session_id}").json()

    response = client.post(f"/api/v1/sessions/{session_id}/start")

    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert response.json()["started_at"] == first["started_at"]


def test_세션_종료를_두_번_해도_종료_시각이_바뀌지_않는다(client):
    session_id = _create_started_session(client)
    first = client.post(f"/api/v1/sessions/{session_id}/end").json()

    second = client.post(f"/api/v1/sessions/{session_id}/end")

    assert second.status_code == 200
    assert second.json()["ended_at"] == first["ended_at"]
    assert second.json()["status"] == "ended"


def test_같은_이벤트_상태로_다시_전이해도_결과가_같다(client, isolated_database):
    session_id = _create_started_session(client)
    event_id = _create_event(
        repository=PostgreSQLMeetingEventRepository(isolated_database),
        utterance_repository=PostgreSQLUtteranceRepository(isolated_database),
        session_id=session_id,
        event_type=EventType.QUESTION,
        title="중복 전이 테스트",
        state=EventState.OPEN,
        priority=EventPriority.QUESTION,
    )
    url = f"/api/v1/sessions/{session_id}/events/{event_id}/transition"
    first = client.post(url, json={"target_state": "answered"})
    assert first.status_code == 200

    second = client.post(url, json={"target_state": "answered"})

    print(f"PROBE event answered->answered: {second.status_code} {second.text[:120]}")
    assert second.status_code == 200
    assert second.json()["state"] == "answered"
