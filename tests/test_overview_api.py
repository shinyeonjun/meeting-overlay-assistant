"""세션 overview API 테스트."""

from tests.support.sample_inputs import (
    ACTION_TEXT,
    DECISION_TEXT,
    QUESTION_TEXT,
    RISK_TEXT,
    SESSION_TITLE,
    TOPIC_TEXT,
)


class TestOverviewApi:
    """세션 overview 조회 테스트."""

    def test_세션_overview를_조회하면_이벤트가_유형별로_묶여서_반환된다(self, client):
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": SESSION_TITLE,
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        session_id = create_response.json()["id"]

        with client.websocket_connect(f"/api/v1/ws/dev-text/{session_id}") as websocket:
            for text in (TOPIC_TEXT, RISK_TEXT, QUESTION_TEXT, DECISION_TEXT, ACTION_TEXT):
                websocket.send_text(text)
                websocket.receive_json()

        response = client.get(f"/api/v1/sessions/{session_id}/overview")

        assert response.status_code == 200
        payload = response.json()
        assert payload["session"]["id"] == session_id
        assert payload["current_topic"] == "로그인 / 오류 논의"
        assert len(payload["questions"]) == 1
        assert len(payload["decisions"]) == 1
        assert len(payload["action_items"]) == 1
        assert len(payload["risks"]) == 1
        assert payload["questions"][0]["state"] == "open"
        assert payload["decisions"][0]["state"] == "confirmed"
        assert payload["risks"][0]["state"] == "open"
        assert "metrics" in payload
        assert payload["metrics"]["recent_average_latency_ms"] is not None
        assert payload["metrics"]["recent_average_latency_ms"] >= 0
        assert payload["metrics"]["recent_utterance_count_by_source"]["system_audio"] >= 5

    def test_설명_발화가_여러개면_current_topic은_요약값을_반환한다(self, client):
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": SESSION_TITLE,
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        session_id = create_response.json()["id"]

        topic_texts = (
            "로그인 오류 원인을 먼저 분석해보죠",
            "로그인 화면에서 세션 만료 오류가 나는 것 같습니다",
            "오류가 사파리 로그인 처리에서 많이 보입니다",
        )

        with client.websocket_connect(f"/api/v1/ws/dev-text/{session_id}") as websocket:
            for text in topic_texts:
                websocket.send_text(text)
                websocket.receive_json()

        response = client.get(f"/api/v1/sessions/{session_id}/overview")

        assert response.status_code == 200
        payload = response.json()
        assert payload["current_topic"] == "로그인 / 오류 논의"
        assert payload["metrics"]["recent_utterance_count_by_source"]["system_audio"] >= 3
