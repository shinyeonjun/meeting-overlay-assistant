"""오디오 계열 shared provider."""

from __future__ import annotations

from functools import lru_cache

from server.app.api.http.wiring import audio_runtime, shared_factories
from server.app.api.http.wiring.persistence import (
    get_event_repository,
    get_transaction_manager,
    get_utterance_repository,
)
from server.app.core.audio_source_policy import resolve_audio_source_policy
from server.app.core.config import settings
from server.app.core.media_service_profiles import (
    resolve_audio_preprocessor_profile,
    resolve_speaker_diarizer_profile,
)

from .analysis import get_shared_analyzer, get_shared_live_event_corrector
from .live_questions import get_shared_live_question_dispatcher
from .runtime import (
    create_postprocessing_speech_to_text_service,
    get_runtime_monitor_service,
    get_speech_to_text_service,
)


def build_audio_pipeline_service(source: str):
    """오디오 소스별 pipeline service를 조립한다."""

    return audio_runtime.build_audio_pipeline_service(
        source=source,
        settings=settings,
        resolve_audio_source_policy=resolve_audio_source_policy,
        speech_to_text_service=get_speech_to_text_service(source),
        analyzer_service=get_shared_analyzer(),
        utterance_repository=get_utterance_repository(),
        event_repository=get_event_repository(),
        transaction_manager=get_transaction_manager(),
        runtime_monitor_service=get_runtime_monitor_service(),
        live_event_corrector=get_shared_live_event_corrector(),
        live_question_dispatcher=get_shared_live_question_dispatcher(),
    )


@lru_cache(maxsize=1)
def get_shared_audio_preprocessor():
    """공용 audio preprocessor singleton을 반환한다."""

    return shared_factories.create_shared_audio_preprocessor(
        settings=settings,
        resolve_audio_preprocessor_profile=resolve_audio_preprocessor_profile,
    )


@lru_cache(maxsize=1)
def get_shared_speaker_diarizer():
    """공용 speaker diarizer singleton을 반환한다."""

    return shared_factories.create_shared_speaker_diarizer(
        settings=settings,
        resolve_speaker_diarizer_profile=resolve_speaker_diarizer_profile,
    )


@lru_cache(maxsize=1)
def get_shared_audio_postprocessing_service():
    """공용 postprocessing service를 반환한다."""

    return shared_factories.create_shared_audio_postprocessing_service(
        settings=settings,
        resolve_audio_source_policy=resolve_audio_source_policy,
        create_audio_preprocessor_service=get_shared_audio_preprocessor,
        create_speaker_diarizer_service=get_shared_speaker_diarizer,
        create_file_speech_to_text_service=lambda: create_postprocessing_speech_to_text_service(
            "file"
        ),
        build_transcription_guard=lambda source_policy: audio_runtime.build_transcription_guard(
            source_policy=source_policy,
            settings=settings,
        ),
    )


@lru_cache(maxsize=1)
def get_shared_speaker_event_projection_service():
    """공용 speaker/event projection service를 반환한다."""

    return shared_factories.create_shared_speaker_event_projection_service(
        analyzer_service=get_shared_analyzer(),
    )
