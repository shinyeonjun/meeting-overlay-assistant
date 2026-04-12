"""HTTP 계층에서 공통 관련 shared factories 구성을 담당한다."""
from __future__ import annotations

from server.app.domain.shared.enums import EventType

from .shared_factory_builders import (
    create_shared_analyzer,
    create_shared_audio_postprocessing_service,
    create_shared_audio_preprocessor,
    create_shared_live_event_corrector as _create_shared_live_event_corrector,
    create_shared_report_refiner,
    create_shared_speaker_diarizer,
    create_shared_speaker_event_projection_service,
    create_shared_topic_summarizer,
)


def create_shared_live_event_corrector(
    *,
    settings,
    resolve_live_event_corrector_service_profile,
    event_repository,
    transaction_manager,
):
    """공용 live event corrector를 만든다."""

    return _create_shared_live_event_corrector(
        settings=settings,
        resolve_live_event_corrector_service_profile=resolve_live_event_corrector_service_profile,
        event_repository=event_repository,
        transaction_manager=transaction_manager,
        EventType=EventType,
    )


__all__ = [
    "create_shared_analyzer",
    "create_shared_audio_postprocessing_service",
    "create_shared_audio_preprocessor",
    "create_shared_live_event_corrector",
    "create_shared_report_refiner",
    "create_shared_speaker_diarizer",
    "create_shared_speaker_event_projection_service",
    "create_shared_topic_summarizer",
]
