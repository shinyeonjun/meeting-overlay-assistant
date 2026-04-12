"""오디오 영역의 final lane adapter 서비스를 제공한다."""
from __future__ import annotations

from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment
from server.app.services.audio.stt.transcription import TranscriptionResult


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
            self._partial_service.reset_stream()
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
