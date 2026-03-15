"""헬스 및 런타임 모니터링 API 테스트."""

from server.app.api.http import dependencies as dependency_module


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

    def test_runtime_monitor_returns_recent_audio_metrics(self, client):
        session_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "운영 모니터 확인 회의",
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        assert session_response.status_code == 200
        session_id = session_response.json()["id"]

        start_response = client.post(f"/api/v1/sessions/{session_id}/start")
        assert start_response.status_code == 200

        monitor = dependency_module.get_runtime_monitor_service()
        monitor.record_final_transcription(
            session_id=session_id,
            final_queue_delay_ms=3200,
            emitted_live_final=False,
            alignment_status="standalone_final",
        )
        monitor.record_preview_backpressure(final_queue_delay_ms=3200, hold_chunks=2)
        monitor.record_rejection(reason="short_final_low_confidence")
        monitor.record_chunk_processed(
            session_id=session_id,
            utterance_count=2,
            event_count=1,
        )
        monitor.record_error(scope="audio_pipeline.process_chunk", message="sample error")

        response = client.get("/api/v1/runtime/monitor")

        assert response.status_code == 200
        payload = response.json()
        assert payload["active_session_count"] == 1
        assert payload["readiness"]["backend_ready"] is True
        assert payload["audio_pipeline"]["recent_final_count"] == 1
        assert payload["audio_pipeline"]["recent_utterance_count"] == 2
        assert payload["audio_pipeline"]["recent_event_count"] == 1
        assert payload["audio_pipeline"]["average_queue_delay_ms"] == 3200.0
        assert payload["audio_pipeline"]["max_queue_delay_ms"] == 3200
        assert payload["audio_pipeline"]["late_final_count"] == 1
        assert payload["audio_pipeline"]["backpressure_count"] == 1
        assert payload["audio_pipeline"]["filtered_count"] == 1
        assert payload["audio_pipeline"]["error_count"] == 1
        assert payload["audio_pipeline"]["standalone_count"] == 1
        assert payload["audio_pipeline"]["standalone_ratio"] == 1.0
        assert payload["audio_pipeline"]["last_chunk_processed_at"] is not None
        assert payload["audio_pipeline"]["last_error_message"] == "audio_pipeline.process_chunk: sample error"
        assert payload["live_stream"]["worker_count"] == 1
        assert payload["live_stream"]["max_running_streams"] >= 1
        assert payload["live_stream"]["active_stream_count"] == 0
        assert payload["live_stream"]["draining_stream_count"] == 0
        assert payload["live_stream"]["coalesced_chunk_count"] == 0
        assert payload["live_stream"]["pending_chunks_per_stream_limit"] >= 1
