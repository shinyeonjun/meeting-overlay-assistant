"""리포트 생성 job 목록 조회(한 번의 요청으로 여러 세션) 테스트."""

from tests.fixtures.support.sessions import create_meeting_session


class TestReportJobsBatchApi:
    def test_job이_없는_세션과_없는_세션_id는_빈_결과로_돌려준다(self, client):
        session_id = create_meeting_session(client, start=False)

        response = client.get(
            "/api/v1/reports/jobs/latest",
            params={"session_ids": [session_id, "session-does-not-exist"]},
        )

        assert response.status_code == 200
        assert response.json() == {}

    def test_session_id가_없으면_빈_결과다(self, client):
        response = client.get("/api/v1/reports/jobs/latest")

        assert response.status_code == 200
        assert response.json() == {}
