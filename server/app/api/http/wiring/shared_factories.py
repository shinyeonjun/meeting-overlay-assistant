"""공유 singleton 생성기."""

from __future__ import annotations

from server.app.domain.shared.enums import EventType
from server.app.services.analysis.analyzers.analyzer_factory import create_meeting_analyzer
from server.app.services.analysis.correction.live_event_correction_service import (
    AsyncLiveEventCorrectionService,
    NoOpLiveEventCorrectionService,
)
from server.app.services.analysis.event_type_policy import (
    filter_insight_event_type_values,
)
from server.app.services.analysis.llm.factories.completion_client_factory import (
    create_llm_completion_client,
)
from server.app.services.audio.preprocessing.audio_preprocessor_factory import (
    create_audio_preprocessor,
)
from server.app.services.diarization.speaker_diarizer_factory import (
    create_speaker_diarizer,
)
from server.app.services.events.meeting_event_service import MeetingEventService
from server.app.services.reports.audio.audio_postprocessing_service import (
    AudioPostprocessingService,
)
from server.app.services.reports.composition.speaker_event_projection_service import (
    SpeakerEventProjectionService,
)
from server.app.services.reports.refinement.report_refiner_factory import (
    create_report_refiner,
)
from server.app.services.reports.refinement.structured_markdown_report_refiner import (
    StructuredMarkdownReportRefiner,
)
from server.app.services.sessions.topic_summarizer import (
    LLMTopicSummarizer,
    NoOpTopicSummarizer,
)


def create_shared_analyzer(*, settings, resolve_analyzer_service_profile):
    """공유 analyzer 인스턴스를 만든다."""

    profile = resolve_analyzer_service_profile(settings)
    return create_meeting_analyzer(
        backend_name=profile.backend_name,
        rules_config_path=str(settings.analysis_rules_config_path),
        llm_provider_backend=profile.completion_client.backend_name,
        llm_model=profile.completion_client.model,
        llm_base_url=profile.completion_client.base_url,
        llm_api_key=profile.completion_client.api_key,
        llm_timeout_seconds=profile.completion_client.timeout_seconds,
        analyzer_chain=profile.analyzer_stages,
    )


def create_shared_audio_preprocessor(*, settings, resolve_audio_preprocessor_profile):
    """공유 audio preprocessor를 만든다."""

    profile = resolve_audio_preprocessor_profile(settings)
    return create_audio_preprocessor(
        profile.backend_name,
        model_path=profile.model_path,
        atten_lim_db=profile.atten_lim_db,
    )


def create_shared_speaker_diarizer(*, settings, resolve_speaker_diarizer_profile):
    """공유 speaker diarizer를 만든다."""

    profile = resolve_speaker_diarizer_profile(settings)
    return create_speaker_diarizer(
        profile.backend_name,
        model_id=profile.model_id,
        auth_token=profile.auth_token,
        device=profile.device,
        default_speaker_label=profile.default_speaker_label,
        worker_python_executable=profile.worker_python_executable,
        worker_script_path=profile.worker_script_path,
        worker_timeout_seconds=profile.worker_timeout_seconds,
    )


def create_shared_audio_postprocessing_service(
    *,
    settings,
    resolve_audio_source_policy,
    create_audio_preprocessor_service,
    create_speaker_diarizer_service,
    create_file_speech_to_text_service,
    build_transcription_guard,
):
    """파일 후처리용 공유 서비스 묶음을 만든다."""

    source_policy = resolve_audio_source_policy("file", settings)
    return AudioPostprocessingService(
        audio_preprocessor=create_audio_preprocessor_service(),
        speaker_diarizer=create_speaker_diarizer_service(),
        speech_to_text_service=create_file_speech_to_text_service(),
        transcription_guard=build_transcription_guard(source_policy),
        expected_sample_rate_hz=settings.stt_sample_rate_hz,
        expected_sample_width_bytes=settings.stt_sample_width_bytes,
        expected_channels=settings.stt_channels,
    )


def create_shared_speaker_event_projection_service(*, analyzer_service):
    """공유 speaker/event projection 서비스를 만든다."""

    return SpeakerEventProjectionService(analyzer=analyzer_service)


def create_shared_report_refiner(*, settings, resolve_report_refiner_service_profile):
    """공유 report refiner를 만든다."""

    profile = resolve_report_refiner_service_profile(settings)
    if profile.backend_name == "noop":
        return StructuredMarkdownReportRefiner()

    backend_name = profile.backend_name
    if backend_name == "llm":
        backend_name = profile.completion_client.backend_name

    return create_report_refiner(
        backend_name=backend_name,
        model=profile.completion_client.model,
        base_url=profile.completion_client.base_url,
        api_key=profile.completion_client.api_key,
        timeout_seconds=profile.completion_client.timeout_seconds,
    )


def create_shared_topic_summarizer(*, settings, resolve_topic_summarizer_service_profile):
    """공유 topic summarizer를 만든다."""

    profile = resolve_topic_summarizer_service_profile(settings)
    if profile.backend_name == "noop":
        return NoOpTopicSummarizer()

    completion_client = create_llm_completion_client(
        backend_name=profile.completion_client.backend_name,
        model=profile.completion_client.model,
        base_url=profile.completion_client.base_url,
        api_key=profile.completion_client.api_key,
        timeout_seconds=profile.completion_client.timeout_seconds,
    )
    return LLMTopicSummarizer(completion_client)


def create_shared_live_event_corrector(
    *,
    settings,
    resolve_live_event_corrector_service_profile,
    event_repository,
    transaction_manager,
):
    """공유 live event corrector를 만든다."""

    profile = resolve_live_event_corrector_service_profile(settings)
    if profile.backend_name == "noop":
        return NoOpLiveEventCorrectionService()

    target_event_types = tuple(
        EventType(event_type)
        for event_type in filter_insight_event_type_values(profile.target_event_types)
    )
    analyzer = create_meeting_analyzer(
        backend_name="llm",
        rules_config_path=str(settings.analysis_rules_config_path),
        llm_provider_backend=profile.completion_client.backend_name,
        llm_model=profile.completion_client.model,
        llm_base_url=profile.completion_client.base_url,
        llm_api_key=profile.completion_client.api_key,
        llm_timeout_seconds=profile.completion_client.timeout_seconds,
    )
    return AsyncLiveEventCorrectionService(
        analyzer=analyzer,
        event_service=MeetingEventService(event_repository),
        transaction_manager=transaction_manager,
        target_event_types=target_event_types,
        min_utterance_confidence=profile.min_utterance_confidence,
        min_text_length=profile.min_text_length,
        max_workers=profile.max_workers,
    )
