"""HTTP 계층에서 공통 관련 audio 구성을 담당한다."""
from __future__ import annotations

from server.app.services.audio.preprocessing.audio_preprocessor_factory import (
    create_audio_preprocessor,
)
from server.app.services.diarization.speaker_diarizer_factory import (
    create_speaker_diarizer,
)
from server.app.services.reports.audio.audio_postprocessing_service import (
    AudioPostprocessingService,
)
from server.app.services.reports.composition.speaker_event_projection_service import (
    SpeakerEventProjectionService,
)


def create_shared_audio_preprocessor(*, settings, resolve_audio_preprocessor_profile):
    """공용 audio preprocessor를 만든다."""

    profile = resolve_audio_preprocessor_profile(settings)
    return create_audio_preprocessor(
        profile.backend_name,
        model_path=profile.model_path,
        atten_lim_db=profile.atten_lim_db,
    )


def create_shared_speaker_diarizer(*, settings, resolve_speaker_diarizer_profile):
    """공용 speaker diarizer를 만든다."""

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
    """파일 후처리용 공용 서비스를 만든다."""

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
    """공용 speaker/event projection 서비스를 만든다."""

    return SpeakerEventProjectionService(analyzer=analyzer_service)
