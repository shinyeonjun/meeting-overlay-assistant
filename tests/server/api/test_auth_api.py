"""공통 영역의 test auth api 동작을 검증한다."""
from __future__ import annotations

import pytest

from server.app.core.config import settings


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
            "department": "플랫폼",
            "client_type": "desktop",
        },
    )
    assert response.status_code == 201
    return response.json()


class TestAuthApi:
    """사내용 최소 인증 흐름을 검증한다."""

    def test_공개_auth_config로_서버_인증_상태를_조회할_수_있다(self, client, auth_enabled):
        response = client.get("/api/v1/auth/config")

        assert response.status_code == 200
        payload = response.json()
        assert payload["enabled"] is True
        assert payload["bootstrap_required"] is True
        assert payload["user_count"] == 0

    def test_초기_관리자_생성은_토큰과_사용자_정보를_반환한다(self, client, auth_enabled):
        payload = _bootstrap_admin(client)

        assert payload["access_token"]
        assert payload["token_type"] == "bearer"
        assert payload["user"]["login_id"] == "owner"
        assert payload["user"]["workspace_name"] == "기본 워크스페이스"
        assert payload["user"]["workspace_role"] == "owner"

    def test_초기_관리자는_한번만_생성할_수_있다(self, client, auth_enabled):
        _bootstrap_admin(client)

        response = client.post(
            "/api/v1/auth/bootstrap-admin",
            json={
                "login_id": "owner2",
                "password": "password123!",
                "display_name": "관리자2",
            },
        )

        assert response.status_code == 409
        assert "한 번만 생성" in response.json()["detail"]

    def test_로그인후_me로_현재_사용자를_조회할_수_있다(self, client, auth_enabled):
        _bootstrap_admin(client)

        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "login_id": "owner",
                "password": "password123!",
                "client_type": "desktop",
            },
        )

        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert me_response.status_code == 200
        assert me_response.json()["display_name"] == "관리자"

    def test_인증_활성화시_보호된_세션_api는_토큰_없이_401이다(self, client, auth_enabled):
        response = client.post(
            "/api/v1/sessions",
            json={
                "title": "인증 필요 회의",
                "mode": "meeting",
                "source": "system_audio",
            },
        )

        assert response.status_code == 401

    def test_인증_사용자_id가_세션_생성자에_기록된다(self, client, auth_enabled):
        bootstrap_payload = _bootstrap_admin(client)
        access_token = bootstrap_payload["access_token"]
        user_id = bootstrap_payload["user"]["id"]

        response = client.post(
            "/api/v1/sessions",
            json={
                "title": "인증 성공 회의",
                "mode": "meeting",
                "source": "system_audio",
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        assert response.json()["title"] == "인증 성공 회의"
        assert response.json()["created_by_user_id"] == user_id

    def test_인증_사용자_id가_리포트_생성자에도_기록된다(self, client, auth_enabled):
        bootstrap_payload = _bootstrap_admin(client)
        access_token = bootstrap_payload["access_token"]
        user_id = bootstrap_payload["user"]["id"]
        headers = {"Authorization": f"Bearer {access_token}"}

        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "리포트 생성자 추적",
                "mode": "meeting",
                "source": "system_audio",
            },
            headers=headers,
        )
        assert create_response.status_code == 200
        session_id = create_response.json()["id"]

        report_response = client.post(
            f"/api/v1/reports/{session_id}/markdown",
            headers=headers,
        )

        assert report_response.status_code == 200
        assert report_response.json()["generated_by_user_id"] == user_id

    def test_로그아웃하면_같은_토큰으로_재호출할_수_없다(self, client, auth_enabled):
        bootstrap_payload = _bootstrap_admin(client)
        access_token = bootstrap_payload["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        logout_response = client.post("/api/v1/auth/logout", headers=headers)
        me_response = client.get("/api/v1/auth/me", headers=headers)

        assert logout_response.status_code == 204
        assert me_response.status_code == 401

    def test_인증_활성화시_runtime_monitor도_토큰_없이_401이다(self, client, auth_enabled):
        response = client.get("/api/v1/runtime/monitor")

        assert response.status_code == 401
