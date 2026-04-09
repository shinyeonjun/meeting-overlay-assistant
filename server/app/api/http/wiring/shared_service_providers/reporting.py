"""리포트/요약 계열 shared provider."""

from __future__ import annotations

from functools import lru_cache

from server.app.api.http.wiring import shared_factories
from server.app.core.ai_service_profiles import (
    resolve_report_refiner_service_profile,
    resolve_topic_summarizer_service_profile,
)
from server.app.core.config import settings
from server.app.services.analysis.llm.factories.completion_client_factory import (
    create_llm_completion_client,
)
from server.app.services.reports.refinement import (
    NoteTranscriptCorrectionConfig,
    NoteTranscriptCorrector,
)


@lru_cache(maxsize=1)
def get_shared_report_refiner():
    """공용 report refiner singleton을 반환한다."""

    return shared_factories.create_shared_report_refiner(
        settings=settings,
        resolve_report_refiner_service_profile=resolve_report_refiner_service_profile,
    )


@lru_cache(maxsize=1)
def get_shared_note_transcript_corrector():
    """공용 note transcript 보정기 singleton을 반환한다."""

    if not settings.note_transcript_correction_enabled:
        return None

    completion_client = create_llm_completion_client(
        backend_name=settings.note_transcript_correction_backend,
        model=settings.note_transcript_correction_model,
        base_url=(
            settings.note_transcript_correction_base_url
            or "http://127.0.0.1:11434/v1"
        ),
        api_key=settings.note_transcript_correction_api_key,
        timeout_seconds=settings.note_transcript_correction_timeout_seconds,
    )
    return NoteTranscriptCorrector(
        completion_client,
        config=NoteTranscriptCorrectionConfig(
            model=settings.note_transcript_correction_model,
            max_window=settings.note_transcript_correction_max_window,
        ),
    )


@lru_cache(maxsize=1)
def get_shared_topic_summarizer():
    """공용 topic summarizer singleton을 반환한다."""

    return shared_factories.create_shared_topic_summarizer(
        settings=settings,
        resolve_topic_summarizer_service_profile=resolve_topic_summarizer_service_profile,
    )
