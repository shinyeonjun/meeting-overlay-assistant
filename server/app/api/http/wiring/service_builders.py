"""HTTP 계층에서 자주 쓰는 service builder 진입점을 다시 내보낸다.

라우터나 dependency 모듈이 builder 세부 파일 구조를 몰라도 되도록,
분산된 builder 함수를 이 모듈에서 한 번 모아준다. import 경로를 얇게
유지하는 것이 목적이지, 새로운 로직을 추가하는 레이어는 아니다.
"""
from __future__ import annotations

from server.app.api.http.wiring.builders import (
    auth_context,
    events_history,
    reporting,
    runtime,
)

build_auth_service = auth_context.build_auth_service
build_session_recovery_service = auth_context.build_session_recovery_service
build_session_service = auth_context.build_session_service
build_meeting_context_service = auth_context.build_meeting_context_service
build_context_catalog_service = auth_context.build_context_catalog_service
build_context_resolution_service = auth_context.build_context_resolution_service
build_participant_followup_service = auth_context.build_participant_followup_service
build_participation_query_service = auth_context.build_participation_query_service

build_runtime_monitor_service = runtime.build_runtime_monitor_service
build_session_finalization_service = runtime.build_session_finalization_service
build_post_meeting_pipeline_service = runtime.build_post_meeting_pipeline_service
build_text_input_pipeline_service = runtime.build_text_input_pipeline_service

build_event_management_service = events_history.build_event_management_service
build_event_lifecycle_service = events_history.build_event_lifecycle_service
build_history_query_service = events_history.build_history_query_service

build_report_service = reporting.build_report_service
build_note_correction_job_service = reporting.build_note_correction_job_service
build_post_meeting_pipeline_recovery_service = (
    reporting.build_post_meeting_pipeline_recovery_service
)
build_report_generation_job_service = reporting.build_report_generation_job_service
build_report_knowledge_indexing_service = (
    reporting.build_report_knowledge_indexing_service
)
build_retrieval_query_service = reporting.build_retrieval_query_service
build_ollama_embedding_service = reporting.build_ollama_embedding_service
build_report_share_service = reporting.build_report_share_service
build_session_overview_service = reporting.build_session_overview_service
