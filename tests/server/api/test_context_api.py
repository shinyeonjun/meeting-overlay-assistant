"""회의 맥락 API 테스트."""

from __future__ import annotations

from server.app.domain.models.meeting_event import MeetingEvent
from server.app.domain.models.report import Report
from server.app.domain.shared.enums import EventPriority, EventState, EventType
from server.app.infrastructure.persistence.postgresql.repositories.events import (
    PostgreSQLMeetingEventRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_report_repository import (
    PostgreSQLReportRepository,
)


class TestContextApi:
    """회사, 상대방, 업무 흐름과 히스토리 연계를 검증한다."""

    def test_회사_상대방_업무흐름을_생성하고_세션에_연결할_수_있다(self, client):
        account_response = client.post(
            "/api/v1/context/accounts",
            json={
                "name": "오픈AI 코리아",
                "description": "사내 AI 도입 논의",
            },
        )
        assert account_response.status_code == 200
        account_payload = account_response.json()

        contact_response = client.post(
            "/api/v1/context/contacts",
            json={
                "account_id": account_payload["id"],
                "name": "김민지",
                "email": "mjk@openai.example",
                "job_title": "대리",
                "department": "전략기획팀",
                "notes": "실무 PM",
            },
        )
        assert contact_response.status_code == 200
        contact_payload = contact_response.json()
        assert contact_payload["account_id"] == account_payload["id"]
        assert contact_payload["department"] == "전략기획팀"

        thread_response = client.post(
            "/api/v1/context/threads",
            json={
                "account_id": account_payload["id"],
                "contact_id": contact_payload["id"],
                "title": "온프렘 AI PoC",
                "summary": "보안 요건과 배포 모델 검토",
            },
        )
        assert thread_response.status_code == 200
        thread_payload = thread_response.json()
        assert thread_payload["contact_id"] == contact_payload["id"]

        session_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "오픈AI 코리아 1차 미팅",
                "mode": "meeting",
                "source": "system_audio",
                "account_id": account_payload["id"],
                "contact_id": contact_payload["id"],
                "context_thread_id": thread_payload["id"],
            },
        )
        assert session_response.status_code == 200
        session_payload = session_response.json()
        assert session_payload["account_id"] == account_payload["id"]
        assert session_payload["contact_id"] == contact_payload["id"]
        assert session_payload["context_thread_id"] == thread_payload["id"]

    def test_상대방만_넣으면_세션_생성시에_회사_id를_자동_보정한다(self, client):
        account_response = client.post(
            "/api/v1/context/accounts",
            json={"name": "캡스 파트너스"},
        )
        account_id = account_response.json()["id"]
        contact_response = client.post(
            "/api/v1/context/contacts",
            json={
                "account_id": account_id,
                "name": "박정훈",
            },
        )
        contact_id = contact_response.json()["id"]

        session_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "후속 미팅",
                "mode": "meeting",
                "source": "system_audio",
                "contact_id": contact_id,
            },
        )

        assert session_response.status_code == 200
        session_payload = session_response.json()
        assert session_payload["contact_id"] == contact_id
        assert session_payload["account_id"] == account_id

    def test_존재하지_않는_회사_맥락으로_세션을_연결하면_400이다(self, client):
        response = client.post(
            "/api/v1/sessions",
            json={
                "title": "잘못된 연결",
                "mode": "meeting",
                "source": "system_audio",
                "account_id": "account-missing",
            },
        )

        assert response.status_code == 400
        assert "회사 맥락을 찾지 못했습니다" in response.json()["detail"]

    def test_선택한_회사_맥락으로_세션_목록을_좁혀_볼_수_있다(self, client):
        account_response = client.post("/api/v1/context/accounts", json={"name": "컨텍스트랩"})
        account_id = account_response.json()["id"]

        matched_session_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "컨텍스트랩 주간 미팅",
                "mode": "meeting",
                "source": "system_audio",
                "account_id": account_id,
            },
        )
        other_session_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "일반 내부 회의",
                "mode": "meeting",
                "source": "system_audio",
            },
        )

        response = client.get(f"/api/v1/sessions?scope=all&account_id={account_id}")

        assert response.status_code == 200
        payload = response.json()
        assert [item["id"] for item in payload["items"]] == [matched_session_response.json()["id"]]
        assert payload["items"][0]["account_id"] == account_id
        assert payload["items"][0]["id"] != other_session_response.json()["id"]

    def test_선택한_회사_맥락으로_회의록_목록을_좁혀_볼_수_있다(self, client, isolated_database, tmp_path):
        account_response = client.post("/api/v1/context/accounts", json={"name": "브랜지텍스"})
        account_id = account_response.json()["id"]

        matched_session_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "브랜지텍스 후속 미팅",
                "mode": "meeting",
                "source": "system_audio",
                "account_id": account_id,
            },
        )
        other_session_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "사내 운영 회의",
                "mode": "meeting",
                "source": "system_audio",
            },
        )

        report_repository = PostgreSQLReportRepository(isolated_database)
        matched_report = report_repository.save(
            Report.create(
                session_id=matched_session_response.json()["id"],
                report_type="markdown",
                version=1,
                file_path=str(tmp_path / "matched.md"),
                insight_source="live_fallback",
            ),
        )
        report_repository.save(
            Report.create(
                session_id=other_session_response.json()["id"],
                report_type="markdown",
                version=1,
                file_path=str(tmp_path / "other.md"),
                insight_source="live_fallback",
            ),
        )

        response = client.get(f"/api/v1/reports?scope=all&account_id={account_id}")

        assert response.status_code == 200
        payload = response.json()
        assert [item["id"] for item in payload["items"]] == [matched_report.id]
        assert payload["items"][0]["session_id"] == matched_session_response.json()["id"]

    def test_맥락_타임라인으로_최근_회의와_회의록을_같이_이어볼_수_있다(
        self,
        client,
        isolated_database,
        tmp_path,
    ):
        account_response = client.post("/api/v1/context/accounts", json={"name": "루프랩"})
        account_id = account_response.json()["id"]
        contact_response = client.post(
            "/api/v1/context/contacts",
            json={
                "account_id": account_id,
                "name": "이서연",
            },
        )
        contact_id = contact_response.json()["id"]
        thread_response = client.post(
            "/api/v1/context/threads",
            json={
                "account_id": account_id,
                "contact_id": contact_id,
                "title": "분기 제안 정리",
            },
        )
        thread_id = thread_response.json()["id"]

        first_session_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "루프랩 1차 제안 미팅",
                "mode": "meeting",
                "source": "system_audio",
                "account_id": account_id,
                "contact_id": contact_id,
                "context_thread_id": thread_id,
            },
        )
        second_session_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "루프랩 후속 정리 미팅",
                "mode": "meeting",
                "source": "mic",
                "account_id": account_id,
                "contact_id": contact_id,
                "context_thread_id": thread_id,
            },
        )

        report_repository = PostgreSQLReportRepository(isolated_database)
        saved_report = report_repository.save(
            Report.create(
                session_id=second_session_response.json()["id"],
                report_type="markdown",
                version=1,
                file_path=str(tmp_path / "timeline.md"),
                insight_source="live_fallback",
            ),
        )
        event_repository = PostgreSQLMeetingEventRepository(isolated_database)
        event_repository.save(
            MeetingEvent.create(
                session_id=second_session_response.json()["id"],
                event_type=EventType.DECISION,
                title="2분기 AI PoC 범위를 확정한다",
                state=EventState.CONFIRMED,
                priority=EventPriority.DECISION,
                source_utterance_id=None,
            ),
        )
        event_repository.save(
            MeetingEvent.create(
                session_id=second_session_response.json()["id"],
                event_type=EventType.ACTION_ITEM,
                title="보안 검토 일정 잡기",
                state=EventState.OPEN,
                priority=EventPriority.ACTION_ITEM,
                source_utterance_id=None,
            ),
        )
        event_repository.save(
            MeetingEvent.create(
                session_id=first_session_response.json()["id"],
                event_type=EventType.RISK,
                title="온프레미스 GPU 수급 지연 가능성",
                state=EventState.RESOLVED,
                priority=EventPriority.RISK,
                source_utterance_id=None,
            ),
        )
        event_repository.save(
            MeetingEvent.create(
                session_id=first_session_response.json()["id"],
                event_type=EventType.QUESTION,
                title="기존 사내 SSO와 연결 가능한가",
                state=EventState.OPEN,
                priority=EventPriority.QUESTION,
                source_utterance_id=None,
            ),
        )

        response = client.get(
            "/api/v1/history/timeline",
            params={
                "scope": "all",
                "account_id": account_id,
                "contact_id": contact_id,
                "context_thread_id": thread_id,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["account_id"] == account_id
        assert payload["contact_id"] == contact_id
        assert payload["context_thread_id"] == thread_id
        assert payload["session_count"] == 2
        assert payload["report_count"] == 1
        assert payload["sessions"][0]["id"] == second_session_response.json()["id"]
        assert payload["sessions"][1]["id"] == first_session_response.json()["id"]
        assert payload["reports"][0]["id"] == saved_report.id
        assert payload["carry_over"]["decisions"][0]["title"] == "2분기 AI PoC 범위를 확정한다"
        assert payload["carry_over"]["action_items"][0]["state"] == "open"
        assert payload["carry_over"]["risks"][0]["state"] == "resolved"
        assert payload["carry_over"]["questions"][0]["title"] == "기존 사내 SSO와 연결 가능한가"
