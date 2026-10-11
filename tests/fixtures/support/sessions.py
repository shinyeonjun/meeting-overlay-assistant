"""API 테스트용 회의 세션 생성 helper."""

from __future__ import annotations

from tests.fixtures.support.sample_inputs import SESSION_TITLE


def create_meeting_session(
    client,
    *,
    title: str = SESSION_TITLE,
    start: bool = True,
    headers: dict[str, str] | None = None,
) -> str:
    """회의 세션을 만들고 필요하면 시작한 뒤 세션 id를 돌려준다."""

    response = client.post(
        "/api/v1/sessions",
        json={"title": title, "mode": "meeting", "source": "system_audio"},
        headers=headers,
    )
    assert response.status_code == 200
    session_id = response.json()["id"]

    if start:
        start_response = client.post(f"/api/v1/sessions/{session_id}/start", headers=headers)
        assert start_response.status_code == 200
    return session_id
