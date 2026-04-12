"""공통 영역의 test authorization api 동작을 검증한다."""
from __future__ import annotations

import pytest

from server.app.api.http import dependencies as dependency_module
from server.app.core.config import settings
from server.app.domain.models.user import UserAccount


@pytest.fixture
def auth_enabled():
    """테스트 동안 인증 기능을 활성화한다."""

    original_auth_enabled = settings.auth_enabled
    object.__setattr__(settings, "auth_enabled", True)
    try:
        yield
    finally:
        object.__setattr__(settings, "auth_enabled", original_auth_enabled)


def _bootstrap_admin(client):
    response = client.post(
        "/api/v1/auth/bootstrap-admin",
        json={
            "login_id": "owner",
            "password": "password123!",
            "display_name": "관리자",
            "job_title": "대표",
            "department": "운영팀",
            "client_type": "desktop",
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_user(*, login_id: str, password: str, display_name: str, workspace_role: str = "member") -> UserAccount:
    auth_service = dependency_module.get_auth_service()
    user = UserAccount.create(
        login_id=login_id,
        display_name=display_name,
        workspace_role=workspace_role,
        job_title="매니저",
        department="운영팀",
    )
    auth_service._repository.create_user_with_password(
        user=user,
        password_hash=auth_service._hash_password(password),
        password_updated_at=auth_service._utc_now_iso(),
    )
    return user


def _login(client, *, login_id: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "login_id": login_id,
            "password": password,
            "client_type": "desktop",
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _create_session(client, *, access_token: str, title: str) -> str:
    response = client.post(
        "/api/v1/sessions",
        json={
            "title": title,
            "mode": "meeting",
            "source": "system_audio",
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    return response.json()["id"]


class TestAuthorizationApi:
    """세션과 리포트의 접근 권한을 검증한다."""

    def test_member_scope_mine_returns_own_sessions_only(self, client, auth_enabled):
        owner_payload = _bootstrap_admin(client)
        owner_token = owner_payload["access_token"]
        member = _create_user(
            login_id="member",
            password="password123!",
            display_name="멤버",
        )
        member_token = _login(client, login_id=member.login_id, password="password123!")

        _create_session(client, access_token=owner_token, title="관리자 회의")
        member_session_id = _create_session(client, access_token=member_token, title="멤버 회의")

        response = client.get(
            "/api/v1/sessions?scope=mine",
            headers={"Authorization": f"Bearer {member_token}"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert [item["id"] for item in payload["items"]] == [member_session_id]
        assert payload["items"][0]["created_by_user_id"] == member.id

    def test_owner_scope_all_returns_all_sessions(self, client, auth_enabled):
        owner_payload = _bootstrap_admin(client)
        owner_token = owner_payload["access_token"]
        _create_user(
            login_id="member",
            password="password123!",
            display_name="멤버",
        )
        member_token = _login(client, login_id="member", password="password123!")

        owner_session_id = _create_session(client, access_token=owner_token, title="관리자 회의")
        member_session_id = _create_session(client, access_token=member_token, title="멤버 회의")

        response = client.get(
            "/api/v1/sessions?scope=all",
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        assert response.status_code == 200
        returned_ids = {item["id"] for item in response.json()["items"]}
        assert {owner_session_id, member_session_id}.issubset(returned_ids)

    def test_member_scope_all_forbidden(self, client, auth_enabled):
        _bootstrap_admin(client)
        _create_user(
            login_id="member",
            password="password123!",
            display_name="멤버",
        )
        member_token = _login(client, login_id="member", password="password123!")

        response = client.get(
            "/api/v1/sessions?scope=all",
            headers={"Authorization": f"Bearer {member_token}"},
        )

        assert response.status_code == 403

    def test_member_cannot_access_other_users_session_resources(self, client, auth_enabled):
        owner_payload = _bootstrap_admin(client)
        owner_token = owner_payload["access_token"]
        _create_user(
            login_id="member",
            password="password123!",
            display_name="멤버",
        )
        member_token = _login(client, login_id="member", password="password123!")

        owner_session_id = _create_session(client, access_token=owner_token, title="관리자 회의")

        overview_response = client.get(
            f"/api/v1/sessions/{owner_session_id}/overview",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        events_response = client.get(
            f"/api/v1/sessions/{owner_session_id}/events",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        report_response = client.post(
            f"/api/v1/reports/{owner_session_id}/markdown",
            headers={"Authorization": f"Bearer {member_token}"},
        )

        assert overview_response.status_code == 403
        assert events_response.status_code == 403
        assert report_response.status_code == 403

    def test_member_scope_mine_returns_own_reports_only(self, client, auth_enabled):
        owner_payload = _bootstrap_admin(client)
        owner_token = owner_payload["access_token"]
        _create_user(
            login_id="member",
            password="password123!",
            display_name="멤버",
        )
        member_token = _login(client, login_id="member", password="password123!")

        owner_session_id = _create_session(client, access_token=owner_token, title="관리자 회의")
        member_session_id = _create_session(client, access_token=member_token, title="멤버 회의")

        owner_report = client.post(
            f"/api/v1/reports/{owner_session_id}/markdown",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        member_report = client.post(
            f"/api/v1/reports/{member_session_id}/markdown",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert owner_report.status_code == 200
        assert member_report.status_code == 200

        response = client.get(
            "/api/v1/reports?scope=mine",
            headers={"Authorization": f"Bearer {member_token}"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert len(payload["items"]) == 1
        assert payload["items"][0]["session_id"] == member_session_id

    def test_member_can_share_own_report(self, client, auth_enabled):
        _bootstrap_admin(client)
        member = _create_user(
            login_id="member",
            password="password123!",
            display_name="멤버",
        )
        recipient = _create_user(
            login_id="recipient",
            password="password123!",
            display_name="수신자",
        )
        member_token = _login(client, login_id=member.login_id, password="password123!")

        session_id = _create_session(client, access_token=member_token, title="멤버 회의")
        report_response = client.post(
            f"/api/v1/reports/{session_id}/markdown",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert report_response.status_code == 200
        report_id = report_response.json()["id"]

        share_response = client.post(
            f"/api/v1/reports/{session_id}/{report_id}/shares",
            json={
                "shared_with_login_id": recipient.login_id,
                "note": "검토 부탁드립니다.",
            },
            headers={"Authorization": f"Bearer {member_token}"},
        )

        assert share_response.status_code == 201
        payload = share_response.json()
        assert payload["report_id"] == report_id
        assert payload["shared_by_user_id"] == member.id
        assert payload["shared_with_user_id"] == recipient.id
        assert payload["note"] == "검토 부탁드립니다."

        list_response = client.get(
            f"/api/v1/reports/{session_id}/{report_id}/shares",
            headers={"Authorization": f"Bearer {member_token}"},
        )

        assert list_response.status_code == 200
        list_payload = list_response.json()
        assert len(list_payload["items"]) == 1
        assert list_payload["items"][0]["shared_with_login_id"] == recipient.login_id

    def test_member_cannot_share_other_users_report(self, client, auth_enabled):
        owner_payload = _bootstrap_admin(client)
        owner_token = owner_payload["access_token"]
        member = _create_user(
            login_id="member",
            password="password123!",
            display_name="멤버",
        )
        recipient = _create_user(
            login_id="recipient",
            password="password123!",
            display_name="수신자",
        )
        member_token = _login(client, login_id=member.login_id, password="password123!")

        session_id = _create_session(client, access_token=owner_token, title="관리자 회의")
        report_response = client.post(
            f"/api/v1/reports/{session_id}/markdown",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert report_response.status_code == 200
        report_id = report_response.json()["id"]

        share_response = client.post(
            f"/api/v1/reports/{session_id}/{report_id}/shares",
            json={"shared_with_login_id": recipient.login_id},
            headers={"Authorization": f"Bearer {member_token}"},
        )

        assert share_response.status_code == 403

    def test_duplicate_share_returns_409(self, client, auth_enabled):
        _bootstrap_admin(client)
        member = _create_user(
            login_id="member",
            password="password123!",
            display_name="멤버",
        )
        recipient = _create_user(
            login_id="recipient",
            password="password123!",
            display_name="수신자",
        )
        member_token = _login(client, login_id=member.login_id, password="password123!")

        session_id = _create_session(client, access_token=member_token, title="멤버 회의")
        report_response = client.post(
            f"/api/v1/reports/{session_id}/markdown",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        report_id = report_response.json()["id"]

        first_response = client.post(
            f"/api/v1/reports/{session_id}/{report_id}/shares",
            json={"shared_with_login_id": recipient.login_id},
            headers={"Authorization": f"Bearer {member_token}"},
        )
        second_response = client.post(
            f"/api/v1/reports/{session_id}/{report_id}/shares",
            json={"shared_with_login_id": recipient.login_id},
            headers={"Authorization": f"Bearer {member_token}"},
        )

        assert first_response.status_code == 201
        assert second_response.status_code == 409

    def test_recipient_can_open_shared_report(self, client, auth_enabled):
        _bootstrap_admin(client)
        member = _create_user(
            login_id="member",
            password="password123!",
            display_name="멤버",
        )
        recipient = _create_user(
            login_id="recipient",
            password="password123!",
            display_name="수신자",
        )
        member_token = _login(client, login_id=member.login_id, password="password123!")
        recipient_token = _login(client, login_id=recipient.login_id, password="password123!")

        session_id = _create_session(client, access_token=member_token, title="멤버 회의")
        report_response = client.post(
            f"/api/v1/reports/{session_id}/markdown",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert report_response.status_code == 200
        report_id = report_response.json()["id"]

        share_response = client.post(
            f"/api/v1/reports/{session_id}/{report_id}/shares",
            json={
                "shared_with_login_id": recipient.login_id,
                "note": "검토 부탁드립니다.",
            },
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert share_response.status_code == 201

        inbox_response = client.get(
            "/api/v1/reports/shared-with-me",
            headers={"Authorization": f"Bearer {recipient_token}"},
        )
        assert inbox_response.status_code == 200
        inbox_items = inbox_response.json()["items"]
        assert len(inbox_items) == 1
        assert inbox_items[0]["report_id"] == report_id
        assert inbox_items[0]["file_name"].endswith(".md")

        opened_report_response = client.get(
            f"/api/v1/reports/shared-with-me/{report_id}",
            headers={"Authorization": f"Bearer {recipient_token}"},
        )
        assert opened_report_response.status_code == 200
        opened_report_payload = opened_report_response.json()
        assert opened_report_payload["id"] == report_id
        assert opened_report_payload["content"] is not None

    def test_unrelated_user_cannot_open_shared_report(self, client, auth_enabled):
        _bootstrap_admin(client)
        member = _create_user(
            login_id="member",
            password="password123!",
            display_name="멤버",
        )
        recipient = _create_user(
            login_id="recipient",
            password="password123!",
            display_name="수신자",
        )
        outsider = _create_user(
            login_id="outsider",
            password="password123!",
            display_name="외부사용자",
        )
        member_token = _login(client, login_id=member.login_id, password="password123!")
        outsider_token = _login(client, login_id=outsider.login_id, password="password123!")

        session_id = _create_session(client, access_token=member_token, title="멤버 회의")
        report_response = client.post(
            f"/api/v1/reports/{session_id}/markdown",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert report_response.status_code == 200
        report_id = report_response.json()["id"]

        share_response = client.post(
            f"/api/v1/reports/{session_id}/{report_id}/shares",
            json={"shared_with_login_id": recipient.login_id},
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert share_response.status_code == 201

        opened_report_response = client.get(
            f"/api/v1/reports/shared-with-me/{report_id}",
            headers={"Authorization": f"Bearer {outsider_token}"},
        )
        assert opened_report_response.status_code == 404
