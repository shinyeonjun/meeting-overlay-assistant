"""공통 영역의 test health api 동작을 검증한다."""
import time

from server.app.api.http import dependencies as dependency_module


class TestHealthApi:
    """HealthApi 동작을 검증한다."""
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
            live_final_compare_count=1,
            live_final_changed=True,
            live_final_similarity=0.82,
            live_final_delay_ms=640,
        )
        monitor.record_preview_stage(
            session_id=session_id,
            stage="ready",
            pending_final_chunk_count=2,
            busy_worker_count=1,
            preview_cycle_id=1,
        )
        time.sleep(0.002)
        monitor.record_preview_stage(
            session_id=session_id,
            stage="picked",
            pending_final_chunk_count=1,
            busy_worker_count=1,
            preview_cycle_id=1,
        )
        time.sleep(0.002)
        monitor.record_preview_stage(session_id=session_id, stage="job_started", preview_cycle_id=1)
        time.sleep(0.002)
        monitor.record_preview_stage(session_id=session_id, stage="sherpa_non_empty", preview_cycle_id=1)
        time.sleep(0.002)
        monitor.record_preview_candidate(session_id=session_id, kind="preview", preview_cycle_id=1)
        monitor.record_preview_candidate(session_id=session_id, kind="live_final", preview_cycle_id=1)
        time.sleep(0.002)
        monitor.record_preview_emitted(session_id=session_id, kind="preview", preview_cycle_id=1)
        monitor.record_preview_emitted(session_id=session_id, kind="live_final", preview_cycle_id=1)
        monitor.record_preview_skip(
            session_id=session_id,
            reason="busy",
            pending_final_chunk_count=3,
            has_pending_preview_chunk=True,
            busy_worker_count=1,
            busy_job_kind="final",
        )
        monitor.record_preview_skip(
            session_id=session_id,
            reason="preferred_final",
            pending_final_chunk_count=2,
            has_pending_preview_chunk=True,
            busy_worker_count=0,
            busy_job_kind=None,
        )
        monitor.record_preview_rejection(
            session_id=session_id,
            reason="preview_guard",
            filter_stage="guard",
        )
        monitor.record_preview_rejection(
            session_id=session_id,
            reason="preview_too_short",
            filter_stage="length",
        )
        monitor.record_preview_backpressure(
            session_id=session_id,
            final_queue_delay_ms=3200,
            hold_chunks=2,
        )
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
        assert payload["audio_pipeline"]["live_final_compare_count"] == 1
        assert payload["audio_pipeline"]["live_final_exact_match_count"] == 0
        assert payload["audio_pipeline"]["live_final_changed_count"] == 1
        assert payload["audio_pipeline"]["live_final_change_ratio"] == 1.0
        assert payload["audio_pipeline"]["live_final_average_similarity"] == 0.82
        assert payload["audio_pipeline"]["live_final_average_delay_ms"] == 640.0
        assert payload["audio_pipeline"]["preview_candidate_count"] == 2
        assert payload["audio_pipeline"]["preview_candidate_preview_count"] == 1
        assert payload["audio_pipeline"]["preview_candidate_live_final_count"] == 1
        assert payload["audio_pipeline"]["preview_first_attempted_anchor_at_ms"] is not None
        assert payload["audio_pipeline"]["preview_timeline_anchor_at_ms"] is not None
        assert payload["audio_pipeline"]["preview_first_productive_gap_ms"] == 0
        assert payload["audio_pipeline"]["preview_empty_cycles_before_first_candidate_count"] == 0
        assert payload["audio_pipeline"]["preview_first_ready_at_ms"] is not None
        assert payload["audio_pipeline"]["preview_first_job_started_at_ms"] is not None
        assert payload["audio_pipeline"]["preview_first_picked_at_ms"] is not None
        assert payload["audio_pipeline"]["preview_first_sherpa_non_empty_at_ms"] is not None
        assert payload["audio_pipeline"]["preview_first_candidate_at_ms"] is not None
        assert payload["audio_pipeline"]["preview_first_ready_relative_ms"] is not None
        assert payload["audio_pipeline"]["preview_first_picked_relative_ms"] is not None
        assert payload["audio_pipeline"]["preview_first_job_started_relative_ms"] is not None
        assert payload["audio_pipeline"]["preview_first_sherpa_non_empty_relative_ms"] is not None
        assert payload["audio_pipeline"]["preview_first_candidate_relative_ms"] is not None
        assert (
            payload["audio_pipeline"]["preview_first_ready_relative_ms"]
            <= payload["audio_pipeline"]["preview_first_picked_relative_ms"]
            <= payload["audio_pipeline"]["preview_first_job_started_relative_ms"]
            <= payload["audio_pipeline"]["preview_first_sherpa_non_empty_relative_ms"]
            <= payload["audio_pipeline"]["preview_first_candidate_relative_ms"]
        )
        assert payload["audio_pipeline"]["preview_first_ready_pending_final_chunk_count"] == 2
        assert payload["audio_pipeline"]["preview_first_ready_busy_worker_count"] == 1
        assert payload["audio_pipeline"]["preview_first_picked_pending_final_chunk_count"] == 1
        assert payload["audio_pipeline"]["preview_first_picked_busy_worker_count"] == 1
        assert payload["audio_pipeline"]["preview_notify_skipped_busy_count"] == 1
        assert payload["audio_pipeline"]["preview_notify_skipped_preferred_final_count"] == 1
        assert payload["audio_pipeline"]["preview_first_busy_skip_at_ms"] is not None
        assert payload["audio_pipeline"]["preview_first_preferred_final_skip_at_ms"] is not None
        assert payload["audio_pipeline"]["preview_first_busy_skip_relative_ms"] is not None
        assert (
            payload["audio_pipeline"]["preview_first_preferred_final_skip_relative_ms"] is not None
        )
        assert payload["audio_pipeline"]["preview_first_busy_skip_pending_final_chunk_count"] == 3
        assert payload["audio_pipeline"]["preview_first_busy_skip_has_pending_preview_chunk"] is True
        assert payload["audio_pipeline"]["preview_first_busy_skip_busy_worker_count"] == 1
        assert payload["audio_pipeline"]["preview_first_busy_skip_busy_job_kind"] == "final"
        assert payload["audio_pipeline"]["preview_first_preferred_final_skip_pending_final_chunk_count"] == 2
        assert payload["audio_pipeline"]["preview_first_preferred_final_skip_has_pending_preview_chunk"] is True
        assert payload["audio_pipeline"]["preview_first_preferred_final_skip_busy_worker_count"] == 0
        assert payload["audio_pipeline"]["preview_first_preferred_final_skip_busy_job_kind"] is None
        assert payload["audio_pipeline"]["preview_emitted_count"] == 2
        assert payload["audio_pipeline"]["preview_emitted_preview_count"] == 1
        assert payload["audio_pipeline"]["preview_emitted_live_final_count"] == 1
        assert payload["audio_pipeline"]["preview_guard_rejected_count"] == 1
        assert payload["audio_pipeline"]["preview_length_rejected_count"] == 1
        assert payload["audio_pipeline"]["preview_backpressure_count"] == 1
        assert payload["audio_pipeline"]["last_chunk_processed_at"] is not None
        assert payload["audio_pipeline"]["last_error_message"] == "audio_pipeline.process_chunk: sample error"
        assert payload["live_stream"]["worker_count"] >= 1
        assert payload["live_stream"]["max_running_streams"] >= 1
        assert payload["live_stream"]["active_stream_count"] == 0
        assert payload["live_stream"]["draining_stream_count"] == 0
        assert payload["live_stream"]["coalesced_chunk_count"] == 0
        assert payload["live_stream"]["pending_chunks_per_stream_limit"] >= 1

    def test_runtime_monitor_session_filter_returns_session_scoped_metrics(self, client):
        session_a_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "세션 A",
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        session_b_response = client.post(
            "/api/v1/sessions",
            json={
                "title": "세션 B",
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        assert session_a_response.status_code == 200
        assert session_b_response.status_code == 200
        session_a_id = session_a_response.json()["id"]
        session_b_id = session_b_response.json()["id"]

        assert client.post(f"/api/v1/sessions/{session_a_id}/start").status_code == 200
        assert client.post(f"/api/v1/sessions/{session_b_id}/start").status_code == 200

        monitor = dependency_module.get_runtime_monitor_service()
        monitor.record_final_transcription(
            session_id=session_a_id,
            final_queue_delay_ms=700,
            emitted_live_final=True,
            alignment_status="matched",
            live_final_compare_count=1,
            live_final_changed=False,
            live_final_similarity=1.0,
            live_final_delay_ms=180,
        )
        monitor.record_chunk_processed(
            session_id=session_a_id,
            utterance_count=1,
            event_count=0,
        )
        monitor.record_final_transcription(
            session_id=session_b_id,
            final_queue_delay_ms=2100,
            emitted_live_final=False,
            alignment_status="standalone_final",
            live_final_compare_count=1,
            live_final_changed=True,
            live_final_similarity=0.4,
            live_final_delay_ms=620,
        )
        monitor.record_preview_stage(
            session_id=session_a_id,
            stage="ready",
            pending_final_chunk_count=0,
            busy_worker_count=0,
            preview_cycle_id=1,
        )
        time.sleep(0.002)
        monitor.record_preview_stage(
            session_id=session_a_id,
            stage="picked",
            pending_final_chunk_count=0,
            busy_worker_count=1,
            preview_cycle_id=1,
        )
        time.sleep(0.002)
        monitor.record_preview_stage(session_id=session_a_id, stage="job_started", preview_cycle_id=1)
        time.sleep(0.002)
        monitor.record_preview_stage(session_id=session_a_id, stage="sherpa_non_empty", preview_cycle_id=1)
        time.sleep(0.002)
        monitor.record_preview_candidate(session_id=session_a_id, kind="preview", preview_cycle_id=1)
        time.sleep(0.002)
        monitor.record_preview_emitted(session_id=session_a_id, kind="preview", preview_cycle_id=1)
        monitor.record_preview_skip(
            session_id=session_b_id,
            reason="busy",
            pending_final_chunk_count=4,
            has_pending_preview_chunk=True,
            busy_worker_count=1,
            busy_job_kind="final",
        )
        monitor.record_preview_rejection(
            session_id=session_b_id,
            reason="preview_too_short",
            filter_stage="length",
        )
        monitor.record_preview_backpressure(
            session_id=session_b_id,
            final_queue_delay_ms=2100,
            hold_chunks=2,
        )
        monitor.record_chunk_processed(
            session_id=session_b_id,
            utterance_count=3,
            event_count=2,
        )

        response = client.get(f"/api/v1/runtime/monitor?session_id={session_a_id}")

        assert response.status_code == 200
        payload = response.json()
        assert payload["audio_pipeline"]["recent_final_count"] == 1
        assert payload["audio_pipeline"]["recent_utterance_count"] == 1
        assert payload["audio_pipeline"]["recent_event_count"] == 0
        assert payload["audio_pipeline"]["average_queue_delay_ms"] == 700.0
        assert payload["audio_pipeline"]["max_queue_delay_ms"] == 700
        assert payload["audio_pipeline"]["late_final_count"] == 0
        assert payload["audio_pipeline"]["matched_count"] == 1
        assert payload["audio_pipeline"]["standalone_count"] == 0
        assert payload["audio_pipeline"]["live_final_compare_count"] == 1
        assert payload["audio_pipeline"]["live_final_exact_match_count"] == 1
        assert payload["audio_pipeline"]["live_final_changed_count"] == 0
        assert payload["audio_pipeline"]["live_final_change_ratio"] == 0.0
        assert payload["audio_pipeline"]["live_final_average_similarity"] == 1.0
        assert payload["audio_pipeline"]["live_final_average_delay_ms"] == 180.0
        assert payload["audio_pipeline"]["preview_candidate_count"] == 1
        assert payload["audio_pipeline"]["preview_candidate_preview_count"] == 1
        assert payload["audio_pipeline"]["preview_candidate_live_final_count"] == 0
        assert payload["audio_pipeline"]["preview_first_attempted_anchor_at_ms"] is not None
        assert payload["audio_pipeline"]["preview_timeline_anchor_at_ms"] is not None
        assert payload["audio_pipeline"]["preview_first_productive_gap_ms"] == 0
        assert payload["audio_pipeline"]["preview_empty_cycles_before_first_candidate_count"] == 0
        assert payload["audio_pipeline"]["preview_first_ready_at_ms"] is not None
        assert payload["audio_pipeline"]["preview_first_job_started_at_ms"] is not None
        assert payload["audio_pipeline"]["preview_first_picked_at_ms"] is not None
        assert payload["audio_pipeline"]["preview_first_sherpa_non_empty_at_ms"] is not None
        assert payload["audio_pipeline"]["preview_first_candidate_at_ms"] is not None
        assert payload["audio_pipeline"]["preview_first_ready_relative_ms"] is not None
        assert payload["audio_pipeline"]["preview_first_picked_relative_ms"] is not None
        assert payload["audio_pipeline"]["preview_first_job_started_relative_ms"] is not None
        assert payload["audio_pipeline"]["preview_first_sherpa_non_empty_relative_ms"] is not None
        assert payload["audio_pipeline"]["preview_first_candidate_relative_ms"] is not None
        assert payload["audio_pipeline"]["preview_first_ready_pending_final_chunk_count"] == 0
        assert payload["audio_pipeline"]["preview_first_ready_busy_worker_count"] == 0
        assert payload["audio_pipeline"]["preview_first_picked_pending_final_chunk_count"] == 0
        assert payload["audio_pipeline"]["preview_first_picked_busy_worker_count"] == 1
        assert payload["audio_pipeline"]["preview_notify_skipped_busy_count"] == 0
        assert payload["audio_pipeline"]["preview_notify_skipped_preferred_final_count"] == 0
        assert payload["audio_pipeline"]["preview_first_busy_skip_at_ms"] is None
        assert payload["audio_pipeline"]["preview_first_preferred_final_skip_at_ms"] is None
        assert payload["audio_pipeline"]["preview_first_busy_skip_pending_final_chunk_count"] is None
        assert payload["audio_pipeline"]["preview_first_busy_skip_has_pending_preview_chunk"] is None
        assert payload["audio_pipeline"]["preview_first_busy_skip_busy_worker_count"] is None
        assert payload["audio_pipeline"]["preview_first_busy_skip_busy_job_kind"] is None
        assert payload["audio_pipeline"]["preview_first_preferred_final_skip_pending_final_chunk_count"] is None
        assert payload["audio_pipeline"]["preview_first_preferred_final_skip_has_pending_preview_chunk"] is None
        assert payload["audio_pipeline"]["preview_first_preferred_final_skip_busy_worker_count"] is None
        assert payload["audio_pipeline"]["preview_first_preferred_final_skip_busy_job_kind"] is None
        assert payload["audio_pipeline"]["preview_emitted_count"] == 1
        assert payload["audio_pipeline"]["preview_emitted_preview_count"] == 1
        assert payload["audio_pipeline"]["preview_emitted_live_final_count"] == 0
        assert payload["audio_pipeline"]["preview_guard_rejected_count"] == 0
        assert payload["audio_pipeline"]["preview_length_rejected_count"] == 0
        assert payload["audio_pipeline"]["preview_backpressure_count"] == 0
        assert payload["audio_pipeline"]["backpressure_count"] == 0
        assert payload["audio_pipeline"]["filtered_count"] == 0
        assert payload["audio_pipeline"]["error_count"] == 0
        assert payload["audio_pipeline"]["last_chunk_processed_at"] is None
        assert payload["audio_pipeline"]["last_error_at"] is None
        assert payload["audio_pipeline"]["last_error_message"] is None
