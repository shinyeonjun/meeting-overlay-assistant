"""공용 singleton builder 모음."""

from .analysis import create_shared_analyzer, create_shared_live_event_corrector
from .audio import (
    create_shared_audio_postprocessing_service,
    create_shared_audio_preprocessor,
    create_shared_speaker_diarizer,
    create_shared_speaker_event_projection_service,
)
from .reporting import (
    create_shared_report_refiner,
    create_shared_topic_summarizer,
    create_shared_workspace_summary_synthesizer,
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
    "create_shared_workspace_summary_synthesizer",
]
