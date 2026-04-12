"""개발용 placeholder STT 구현."""

from __future__ import annotations

from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment
from server.app.services.audio.stt.transcription import SpeechToTextService, TranscriptionResult


class PlaceholderSpeechToTextService(SpeechToTextService):
    """텍스트 바이트를 그대로 복원하는 개발용 STT 구현."""

    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        """세그먼트를 텍스트로 변환한다."""
        try:
            text = segment.raw_bytes.decode("utf-8").strip()
        except UnicodeDecodeError:
            text = ""

        if not text:
            return TranscriptionResult(
                text="[음성 입력은 수신했지만 텍스트로 복원하지 못했습니다.]",
                confidence=0.1,
            )

        return TranscriptionResult(text=text, confidence=0.95)

