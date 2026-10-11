"""오디오 WebSocket 테스트."""

from tests.fixtures.support.sample_inputs import QUESTION_TEXT, SESSION_TITLE


class TestAudioWebSocketApi:
    """개발용 텍스트 입력 WebSocket 테스트."""

    def test_텍스트를_보내면_utterance와_event를_반환한다(self, client):
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": SESSION_TITLE,
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        session_id = create_response.json()["id"]
        start_response = client.post(f"/api/v1/sessions/{session_id}/start")

        assert start_response.status_code == 200

        with client.websocket_connect(f"/api/v1/ws/text/{session_id}") as websocket:
            websocket.send_text(QUESTION_TEXT)
            payload = websocket.receive_json()

        assert payload["session_id"] == session_id
        assert payload["input_source"] == "system_audio"
        assert len(payload["utterances"]) == 1
        assert payload["utterances"][0]["text"] == QUESTION_TEXT
        assert payload["utterances"][0]["input_source"] == "system_audio"
        assert len(payload["events"]) == 1
        assert payload["events"][0]["type"] == "question"

    def test_알_수_없는_input_source는_연결을_4400으로_거부한다(self, client):
        from starlette.websockets import WebSocketDisconnect
        import pytest

        create_response = client.post(
            "/api/v1/sessions",
            json={"title": SESSION_TITLE, "mode": "meeting", "source": "system_audio"},
        )
        session_id = create_response.json()["id"]
        client.post(f"/api/v1/sessions/{session_id}/start")

        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect(
                f"/api/v1/ws/text/{session_id}?input_source=bogus"
            ) as websocket:
                websocket.receive_json()

        assert excinfo.value.code == 4400
