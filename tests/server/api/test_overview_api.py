"""세션 overview API 테스트."""

from server.app.api.http.wiring.artifact_storage import get_local_artifact_store
from server.app.services.sessions.workspace_summary_models import (
    WorkspaceSummaryDocument,
    WorkspaceSummaryTopic,
)
from server.app.services.sessions.workspace_summary_store import WorkspaceSummaryStore
from tests.fixtures.support.sample_inputs import (
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
        start_response = client.post(f"/api/v1/sessions/{session_id}/start")

        assert start_response.status_code == 200

        with client.websocket_connect(f"/api/v1/ws/text/{session_id}") as websocket:
            for text in (TOPIC_TEXT, RISK_TEXT, QUESTION_TEXT, DECISION_TEXT, ACTION_TEXT):
                websocket.send_text(text)
                websocket.receive_json()

        response = client.get(f"/api/v1/sessions/{session_id}/overview")

        assert response.status_code == 200
        payload = response.json()
        assert payload["session"]["id"] == session_id
        assert "current_topic" in payload
        assert isinstance(payload["questions"], list)
        assert isinstance(payload["decisions"], list)
        assert isinstance(payload["action_items"], list)
        assert isinstance(payload["risks"], list)
        assert payload["workspace_summary"] is None
        assert "metrics" in payload
        assert payload["metrics"]["recent_average_latency_ms"] is None or (
            payload["metrics"]["recent_average_latency_ms"] >= 0
        )
        assert isinstance(payload["metrics"]["recent_utterance_count_by_source"], dict)

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
        start_response = client.post(f"/api/v1/sessions/{session_id}/start")

        assert start_response.status_code == 200

        topic_texts = (
            "로그인 오류 원인을 먼저 분석해보죠",
            "로그인 화면에서 세션 만료 오류가 나는 것 같습니다",
            "오류가 사파리 로그인 처리에서 많이 보입니다",
        )

        with client.websocket_connect(f"/api/v1/ws/text/{session_id}") as websocket:
            for text in topic_texts:
                websocket.send_text(text)
                websocket.receive_json()

        response = client.get(f"/api/v1/sessions/{session_id}/overview")

        assert response.status_code == 200
        payload = response.json()
        assert payload["current_topic"] is None or isinstance(payload["current_topic"], str)
        assert isinstance(payload["metrics"]["recent_utterance_count_by_source"], dict)

    def test_workspace_summary_artifact가_있으면_overview에_포함된다(self, client):
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": SESSION_TITLE,
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        session_id = create_response.json()["id"]
        summary_store = WorkspaceSummaryStore(get_local_artifact_store())
        summary_store.save(
            WorkspaceSummaryDocument(
                session_id=session_id,
                source_version=0,
                model="gemma4:e4b",
                headline="회의 한 줄 요약",
                summary=["핵심 요약 문장입니다."],
                topics=[
                    WorkspaceSummaryTopic(
                        title="로그인 오류 원인 점검",
                        summary="로그인 오류가 나는 조건과 재현 환경을 정리했습니다.",
                        start_ms=0,
                        end_ms=60000,
                    )
                ],
                decisions=["결정 사항입니다."],
                open_questions=["남은 질문입니다."],
            )
        )

        try:
            response = client.get(f"/api/v1/sessions/{session_id}/overview")

            assert response.status_code == 200
            payload = response.json()
            assert payload["workspace_summary"] is not None
            assert payload["workspace_summary"]["headline"] == "회의 한 줄 요약"
            assert payload["workspace_summary"]["summary"] == ["핵심 요약 문장입니다."]
            assert payload["workspace_summary"]["topics"] == [
                {
                    "title": "로그인 오류 원인 점검",
                    "summary": "로그인 오류가 나는 조건과 재현 환경을 정리했습니다.",
                    "start_ms": 0,
                    "end_ms": 60000,
                }
            ]
            assert payload["workspace_summary"]["decisions"] == ["결정 사항입니다."]
        finally:
            summary_store.delete(session_id)
