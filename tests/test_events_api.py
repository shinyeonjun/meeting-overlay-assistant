"""이벤트 관리 API 테스트."""

from tests.support.sample_inputs import (
    ACTION_TEXT,
    DECISION_TEXT,
    QUESTION_TEXT,
    SESSION_TITLE,
)


class TestEventsApi:
    """이벤트 조회, 수정, 삭제 API를 검증한다."""

    def test_세션_이벤트_목록을_조회할_수_있다(self, client):
        session_id = _create_session(client)

        with client.websocket_connect(f"/api/v1/ws/text/{session_id}") as websocket:
            for text in (QUESTION_TEXT, DECISION_TEXT, ACTION_TEXT):
                websocket.send_text(text)
                websocket.receive_json()

        response = client.get(f"/api/v1/sessions/{session_id}/events")

        assert response.status_code == 200
        payload = response.json()
        assert len(payload["items"]) == 1
        assert {item["event_type"] for item in payload["items"]} == {"question"}
        assert {item["insight_scope"] for item in payload["items"]} == {"live"}

    def test_타입과_상태로_이벤트를_필터링할_수_있다(self, client):
        session_id = _create_session(client)

        with client.websocket_connect(f"/api/v1/ws/text/{session_id}") as websocket:
            for text in (QUESTION_TEXT, DECISION_TEXT):
                websocket.send_text(text)
                websocket.receive_json()

        response = client.get(
            f"/api/v1/sessions/{session_id}/events",
            params={"event_type": "question", "state": "open"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert len(payload["items"]) == 1
        assert payload["items"][0]["event_type"] == "question"
        assert payload["items"][0]["state"] == "open"

    def test_이벤트를_patch로_수정할_수_있다(self, client):
        session_id = _create_session(client)

        with client.websocket_connect(f"/api/v1/ws/text/{session_id}") as websocket:
            websocket.send_text(QUESTION_TEXT)
            websocket.receive_json()

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
        assert payload["assignee"] is None
        assert payload["due_date"] is None
        assert payload["evidence_text"] == "사파리에서만 재현되는지 다시 확인해 주세요."
        assert payload["priority"] == 70

    def test_이벤트_타입을_바꾸면_priority도_기본값으로_갱신된다(self, client):
        session_id = _create_session(client)

        with client.websocket_connect(f"/api/v1/ws/text/{session_id}") as websocket:
            websocket.send_text(QUESTION_TEXT)
            websocket.receive_json()

        list_response = client.get(f"/api/v1/sessions/{session_id}/events")
        event_id = list_response.json()["items"][0]["id"]

        response = client.patch(
            f"/api/v1/sessions/{session_id}/events/{event_id}",
            json={"event_type": "risk"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["event_type"] == "risk"
        assert payload["priority"] == 80

    def test_이벤트를_삭제할_수_있다(self, client):
        session_id = _create_session(client)

        with client.websocket_connect(f"/api/v1/ws/text/{session_id}") as websocket:
            websocket.send_text(QUESTION_TEXT)
            websocket.receive_json()

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
    return response.json()["id"]
