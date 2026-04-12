"""Reporting 관련 shared singleton provider를 제공한다.

리포트 refiner, topic summarizer, note transcript corrector처럼 상대적으로
무거운 객체를 프로세스 단위 singleton으로 관리해서, 워커와 API가 같은
설정을 재사용하도록 만든다.
"""
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
    """공용 note transcript 보정기 singleton을 반환한다.

    correction 기능이 꺼져 있으면 명시적으로 `None`을 반환해서, 상위 서비스가
    no-op 단계로 처리할 수 있게 한다.
    """

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
            max_candidates=settings.note_transcript_correction_max_candidates,
            max_confidence_for_correction=(
                settings.note_transcript_correction_max_confidence_for_correction
            ),
            short_utterance_max_chars=(
                settings.note_transcript_correction_short_utterance_max_chars
            ),
        ),
    )


@lru_cache(maxsize=1)
def get_shared_topic_summarizer():
    """공용 topic summarizer singleton을 반환한다."""

    return shared_factories.create_shared_topic_summarizer(
        settings=settings,
        resolve_topic_summarizer_service_profile=resolve_topic_summarizer_service_profile,
    )
