"""hybrid runtime final lane 어댑터."""

from __future__ import annotations

from server.app.contexts.live_capture.application.audio.segmentation.speech_segmenter import SpeechSegment
from server.app.contexts.live_capture.application.audio.stt.transcription import TranscriptionResult


def reset_partial_stream_after(partial_service, segment: SpeechSegment) -> None:
    """확정 구간이 끝난 오디오 위치를 아는 partial 엔진에는 그 위치를 넘겨 리셋한다."""

    reset_stream_at = getattr(partial_service, "reset_stream_at", None)
    if callable(reset_stream_at) and segment.stream_end_sample is not None:
        reset_stream_at(segment.stream_end_sample)
        return
    partial_service.reset_stream()


class HybridFinalLaneSpeechToTextService:
    """하이브리드 runtime에서 final lane만 분리해 쓰는 어댑터."""

    def __init__(
        self,
        *,
        final_service,
        partial_service,
        reset_partial_stream_on_final: bool,
    ) -> None:
        self._final_service = final_service
        self._partial_service = partial_service
        self._reset_partial_stream_on_final = reset_partial_stream_on_final

    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        result = self._final_service.transcribe(segment)
        if self._reset_partial_stream_on_final:
            reset_partial_stream_after(self._partial_service, segment)
        return result

    def reset_stream(self) -> None:
        reset_final_stream = getattr(self._final_service, "reset_stream", None)
        if callable(reset_final_stream):
            reset_final_stream()

    @property
    def backend_name(self) -> str:
        backend_name = getattr(self._final_service, "backend_name", None)
        if isinstance(backend_name, str) and backend_name.strip():
            return backend_name.strip()
        return type(self._final_service).__name__
