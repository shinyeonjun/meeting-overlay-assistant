"""공통 영역의 test history api 동작을 검증한다."""
from __future__ import annotations


class TestHistoryApi:
    """history timeline 응답의 핵심 필드를 검증한다."""

    def test_history_timeline은_retrieval_brief를_항상_포함한다(self, client):
        account_response = client.post(
            "/api/v1/context/accounts",
            json={"name": "리트리벌 테스트"},
        )
        assert account_response.status_code == 200
        account_id = account_response.json()["id"]

        response = client.get(
            "/api/v1/history/timeline",
            params={
                "scope": "all",
                "account_id": account_id,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["account_id"] == account_id
        assert payload["retrieval_brief"]["query"] is None
        assert payload["retrieval_brief"]["result_count"] == 0
        assert payload["retrieval_brief"]["items"] == []
