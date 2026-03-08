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

        with client.websocket_connect(f"/api/v1/ws/dev-text/{session_id}") as websocket:
            for text in (QUESTION_TEXT, DECISION_TEXT, ACTION_TEXT):
                websocket.send_text(text)
                websocket.receive_json()

        response = client.get(f"/api/v1/sessions/{session_id}/events")

        assert response.status_code == 200
        payload = response.json()
        assert len(payload["items"]) == 3
        assert {item["event_type"] for item in payload["items"]} == {
            "question",
            "decision",
            "action_item",
        }
        assert {item["insight_scope"] for item in payload["items"]} == {"live"}

    def test_타입과_상태로_이벤트를_필터링할_수_있다(self, client):
        session_id = _create_session(client)

        with client.websocket_connect(f"/api/v1/ws/dev-text/{session_id}") as websocket:
            for text in (QUESTION_TEXT, DECISION_TEXT):
                websocket.send_text(text)
                websocket.receive_json()

        response = client.get(
            f"/api/v1/sessions/{session_id}/events",
            params={"event_type": "decision", "state": "confirmed"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert len(payload["items"]) == 1
        assert payload["items"][0]["event_type"] == "decision"
        assert payload["items"][0]["state"] == "confirmed"

    def test_이벤트를_patch로_수정할_수_있다(self, client):
        session_id = _create_session(client)

        with client.websocket_connect(f"/api/v1/ws/dev-text/{session_id}") as websocket:
            websocket.send_text(ACTION_TEXT)
            websocket.receive_json()

        list_response = client.get(f"/api/v1/sessions/{session_id}/events")
        event_id = list_response.json()["items"][0]["id"]

        response = client.patch(
            f"/api/v1/sessions/{session_id}/events/{event_id}",
            json={
                "title": "민수가 금요일까지 일정표를 정리한다.",
                "state": "confirmed",
                "assignee": "민수",
                "due_date": "2026-03-14",
                "evidence_text": "민수가 금요일까지 정리해 주세요.",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["title"] == "민수가 금요일까지 일정표를 정리한다."
        assert payload["state"] == "confirmed"
        assert payload["assignee"] == "민수"
        assert payload["due_date"] == "2026-03-14"
        assert payload["evidence_text"] == "민수가 금요일까지 정리해 주세요."
        assert payload["priority"] == 90

    def test_이벤트_타입을_바꾸면_priority도_기본값으로_갱신된다(self, client):
        session_id = _create_session(client)

        with client.websocket_connect(f"/api/v1/ws/dev-text/{session_id}") as websocket:
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

        with client.websocket_connect(f"/api/v1/ws/dev-text/{session_id}") as websocket:
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
