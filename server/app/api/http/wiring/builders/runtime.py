"""runtime과 후처리 pipeline 관련 builder."""

from __future__ import annotations

from server.app.services.audio.pipeline.orchestrators.audio_pipeline_service import (
    AudioPipelineService,
)
from server.app.services.observability.runtime.runtime_monitor_service import (
    RuntimeMonitorService,
)
from server.app.services.post_meeting.post_meeting_pipeline_service import (
    PostMeetingPipelineService,
)
from server.app.services.sessions.session_finalization_service import (
    SessionFinalizationService,
)


def build_runtime_monitor_service() -> RuntimeMonitorService:
    """공용 runtime monitor 서비스를 생성한다."""

    return RuntimeMonitorService()


def build_session_finalization_service(
    *,
    session_service,
    session_post_processing_job_service,
    participant_followup_service,
) -> SessionFinalizationService:
    """세션 종료 후속 서비스를 조립한다."""

    return SessionFinalizationService(
        session_service=session_service,
        session_post_processing_job_service=session_post_processing_job_service,
        participant_followup_service=participant_followup_service,
    )


def build_post_meeting_pipeline_service(
    *,
    session_service,
    session_post_processing_job_service,
    participant_followup_service,
) -> PostMeetingPipelineService:
    """회의 종료 후처리 pipeline 서비스를 조립한다."""

    return PostMeetingPipelineService(
        session_service=session_service,
        session_post_processing_job_service=session_post_processing_job_service,
        participant_followup_service=participant_followup_service,
    )


def build_text_input_pipeline_service(
    *,
    analyzer_service,
    event_repository,
    utterance_repository,
    transcription_guard,
    transaction_manager,
    runtime_monitor_service,
    placeholder_pipeline_factory,
) -> AudioPipelineService:
    """텍스트 입력용 placeholder pipeline을 조립한다."""

    return placeholder_pipeline_factory(
        analyzer_service=analyzer_service,
        event_repository=event_repository,
        utterance_repository=utterance_repository,
        transcription_guard=transcription_guard,
        transaction_manager=transaction_manager,
        runtime_monitor_service=runtime_monitor_service,
    )
