"""오디오 WebSocket 테스트."""

import pytest
from starlette.websockets import WebSocketDisconnect

from tests.fixtures.support.sample_inputs import QUESTION_TEXT, SESSION_TITLE


class TestAudioWebSocketApi:
    """개발용 텍스트 입력 WebSocket 테스트."""

    def test_텍스트를_보내면_mvp_기본값에서는_utterance만_반환한다(self, client):
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
        assert payload["events"] == []

    def test_mic_audio_websocket은_fallback_비활성_상태에서_차단된다(self, client):
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "mic fallback 차단 테스트",
                "mode": "meeting",
                "source": "mic",
            },
        )
        session_id = create_response.json()["id"]
        start_response = client.post(f"/api/v1/sessions/{session_id}/start")

        assert start_response.status_code == 200

        with pytest.raises(WebSocketDisconnect) as error:
            with client.websocket_connect(
                f"/api/v1/ws/audio/{session_id}?input_source=mic"
            ) as websocket:
                websocket.receive_text()

        assert error.value.code == 4420
