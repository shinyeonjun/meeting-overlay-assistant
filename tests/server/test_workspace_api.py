"""워크스페이스 overview API 테스트."""

from tests.fixtures.support.sample_inputs import DECISION_TEXT


class TestWorkspaceApi:
    """웹 워크스페이스 집계 응답을 검증한다."""

    def test_workspace_overview가_요약과_status를_반환한다(self, client):
        account_response = client.post(
            "/api/v1/context/accounts",
            json={"name": "워크스페이스 overview 테스트"},
        )
        assert account_response.status_code == 200
        account_id = account_response.json()["id"]

        session_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "overview 세션",
                "mode": "meeting",
                "source": "system_audio",
                "account_id": account_id,
            },
        )
        assert session_response.status_code == 200

        response = client.get(
            "/api/v1/workspace/overview",
            params={
                "scope": "all",
                "account_id": account_id,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["workspace_id"] == "workspace-default"
        assert payload["account_id"] == account_id
        assert payload["summary"]["active_session_count"] == 0
        assert payload["summary"]["loaded_session_count"] == 1
        assert payload["summary"]["report_count"] == 0
        assert len(payload["sessions"]) == 1
        session_id = payload["sessions"][0]["id"]
        assert payload["sessions"][0]["title"] == "overview 세션"
        assert payload["report_statuses"][session_id]["status"] == "pending"
        assert payload["reports"] == []
        assert payload["retrieval_brief"]["result_count"] == 0

    def test_workspace_overview_active_session_count는_scope를_반영한다(self, client):
        session_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "running session",
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        assert session_response.status_code == 200
        session_id = session_response.json()["id"]

        start_response = client.post(f"/api/v1/sessions/{session_id}/start")
        assert start_response.status_code == 200

        response = client.get("/api/v1/workspace/overview", params={"scope": "mine"})

        assert response.status_code == 200
        payload = response.json()
        assert payload["summary"]["active_session_count"] == 1

    def test_workspace_overview의_report_count는_limit과_무관한_전체_개수다(self, client):
        session_a = self._create_session(client, title="report a")
        session_b = self._create_session(client, title="report b")

        self._ingest_live_text(client, session_a, DECISION_TEXT)
        self._ingest_live_text(client, session_b, DECISION_TEXT)

        assert client.post(f"/api/v1/reports/{session_a}/markdown").status_code == 200
        assert client.post(f"/api/v1/reports/{session_b}/markdown").status_code == 200

        response = client.get(
            "/api/v1/workspace/overview",
            params={
                "scope": "all",
                "limit": 1,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert len(payload["reports"]) == 1
        assert payload["summary"]["report_count"] == 2

    def test_workspace_overview_include플래그로_보조_데이터를_건너뛴다(self, client):
        session_id = self._create_session(client, title="minimal overview")

        response = client.get(
            "/api/v1/workspace/overview",
            params={
                "scope": "all",
                "include_reports": "false",
                "include_carry_over": "false",
                "include_retrieval_brief": "false",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert [item["id"] for item in payload["sessions"]] == [session_id]
        assert payload["reports"] == []
        assert payload["carry_over"] == {
            "decisions": [],
            "action_items": [],
            "risks": [],
            "questions": [],
        }
        assert payload["retrieval_brief"] == {
            "query": None,
            "result_count": 0,
            "items": [],
        }

    @staticmethod
    def _create_session(client, *, title: str) -> str:
        session_response = client.post(
            "/api/v1/sessions",
            json={
                "title": title,
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        assert session_response.status_code == 200
        session_id = session_response.json()["id"]

        start_response = client.post(f"/api/v1/sessions/{session_id}/start")
        assert start_response.status_code == 200
        return session_id

    @staticmethod
    def _ingest_live_text(client, session_id: str, text: str) -> None:
        with client.websocket_connect(f"/api/v1/ws/text/{session_id}") as websocket:
            websocket.send_text(text)
            websocket.receive_json()
