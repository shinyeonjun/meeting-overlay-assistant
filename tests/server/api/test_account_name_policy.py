"""같은 워크스페이스의 활성 계정 이름 중복 정책."""

from __future__ import annotations


def _create_account(client, name: str):
    return client.post("/api/v1/context/accounts", json={"name": name})


def test_같은_이름의_계정을_두_번_만들면_두_번째는_409다(client):
    assert _create_account(client, "ACME").status_code == 200

    second = _create_account(client, "ACME")

    assert second.status_code == 409
    assert "이미 있습니다" in second.json()["detail"]


def test_앞뒤_공백과_대소문자만_다른_이름도_중복이다(client):
    assert _create_account(client, "Acme Corp").status_code == 200

    assert _create_account(client, "  acme corp  ").status_code == 409


def test_다른_이름이면_생성된다(client):
    assert _create_account(client, "ACME").status_code == 200

    assert _create_account(client, "Globex").status_code == 200


def test_계정_목록에는_중복이_하나만_남는다(client):
    _create_account(client, "ACME")
    _create_account(client, "ACME")

    listed = client.get("/api/v1/context/accounts").json()
    names = [item["name"] for item in listed["items"]] if isinstance(listed, dict) else [item["name"] for item in listed]
    assert names.count("ACME") == 1
