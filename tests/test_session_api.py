"""세션 API 테스트"""


class TestSessionApi:
    """세션 생성과 종료 API를 검증한다."""

    def test_세션_생성_api를_호출하면_running_세션을_반환한다(self, client):
        response = client.post(
            "/api/v1/sessions",
            json={
                "title": "테스트 회의",
                "mode": "meeting",
                "source": "system_audio",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["title"] == "테스트 회의"
        assert payload["status"] == "running"
        assert payload["id"].startswith("session-")

    def test_세션_종료_api를_호출하면_ended_상태만_반환한다(self, client):
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "종료 테스트 회의",
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        session_id = create_response.json()["id"]

        response = client.post(f"/api/v1/sessions/{session_id}/end")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ended"
        assert payload["ended_at"] is not None

        reports_response = client.get(f"/api/v1/reports/{session_id}")
        reports_payload = reports_response.json()
        assert reports_response.status_code == 200
        assert reports_payload["items"] == []

    def test_이미_종료된_세션을_다시_종료해도_리포트가_자동_생성되지_않는다(self, client):
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "중복 종료 테스트",
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        session_id = create_response.json()["id"]

        first_end_response = client.post(f"/api/v1/sessions/{session_id}/end")
        second_end_response = client.post(f"/api/v1/sessions/{session_id}/end")

        assert first_end_response.status_code == 200
        assert second_end_response.status_code == 200
        assert first_end_response.json()["ended_at"] == second_end_response.json()["ended_at"]

        reports_response = client.get(f"/api/v1/reports/{session_id}")
        reports_payload = reports_response.json()
        assert reports_payload["items"] == []

    def test_mic_and_audio_소스로_세션을_생성할_수_있다(self, client):
        response = client.post(
            "/api/v1/sessions",
            json={
                "title": "혼합 입력 테스트",
                "mode": "meeting",
                "source": "mic_and_audio",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["source"] == "mic_and_audio"
