class TestHealthApi:
    def test_health_check_returns_ok(self, client):
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_runtime_readiness_returns_preload_state(self, client):
        response = client.get("/api/v1/runtime/readiness")

        assert response.status_code == 200
        payload = response.json()
        assert "backend_ready" in payload
        assert "warming" in payload
        assert "stt_ready" in payload
        assert "preloaded_sources" in payload
        assert isinstance(payload["preloaded_sources"], dict)
