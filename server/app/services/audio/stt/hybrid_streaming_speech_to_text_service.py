"""빠른 partial과 무거운 final을 결합하는 하이브리드 STT 서비스."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from server.app.services.audio.stt.hybrid.final_lane_adapter import (
    HybridFinalLaneSpeechToTextService,
)
from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment
from server.app.services.audio.stt.transcription import (
    SpeechToTextService,
    StreamingSpeechToTextService,
    TranscriptionResult,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HybridStreamingConfig:
    """하이브리드 STT 결합 설정."""

    reset_partial_stream_on_final: bool = True


class HybridStreamingSpeechToTextService:
    """partial 전용 엔진과 final 전용 엔진을 결합한다."""

    def __init__(
        self,
        *,
        config: HybridStreamingConfig,
        partial_service: StreamingSpeechToTextService,
        final_service: SpeechToTextService,
    ) -> None:
        self._config = config
        self._partial_service = partial_service
        self._final_service = final_service
        logger.info(
            "하이브리드 STT 초기화: partial_service=%s final_service=%s reset_partial_on_final=%s",
            type(partial_service).__name__,
            type(final_service).__name__,
            config.reset_partial_stream_on_final,
        )

    def preview_chunk(self, chunk: bytes) -> list[TranscriptionResult]:
        """빠른 partial 엔진에 chunk를 전달한다."""

        return self._partial_service.preview_chunk(chunk)

    def preload(self) -> None:
        """내부 partial/final 엔진이 지원하면 함께 예열한다."""

        partial_preload = getattr(self._partial_service, "preload", None)
        if callable(partial_preload):
            partial_preload()

        final_preload = getattr(self._final_service, "preload", None)
        if callable(final_preload):
            final_preload()

    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        """무거운 final 엔진으로 확정 전사를 생성한다."""

        result = self._final_service.transcribe(segment)
        if self._config.reset_partial_stream_on_final:
            self.reset_stream()
        return result

    def reset_stream(self) -> None:
        """partial 스트림 상태를 초기화한다."""

        self._partial_service.reset_stream()
        reset_final_stream = getattr(self._final_service, "reset_stream", None)
        if callable(reset_final_stream):
            reset_final_stream()

    def split_runtime_lane_services(
        self,
    ) -> tuple[StreamingSpeechToTextService, SpeechToTextService]:
        """runtime preview/final lane에서 사용할 서비스를 분리해 반환한다."""

        return (
            self._partial_service,
            HybridFinalLaneSpeechToTextService(
                final_service=self._final_service,
                partial_service=self._partial_service,
                reset_partial_stream_on_final=self._config.reset_partial_stream_on_final,
            ),
        )
