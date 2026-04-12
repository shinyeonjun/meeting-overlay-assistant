"""오디오 영역의 test openai compatible audio transcription service 동작을 검증한다."""
from __future__ import annotations

import json

from server.app.services.audio.stt.openai_compatible_audio_transcription_service import (
    OpenAICompatibleAudioTranscriptionService,
)
from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment


class TestOpenAICompatibleAudioTranscriptionService:
    """OpenAI 호환 STT 호출을 검증한다."""

    def test_audio_transcriptions_응답에서_text를_추출한다(self):
        transport = StubUrlopen({"text": "안녕하세요", "confidence": 0.93})
        service = OpenAICompatibleAudioTranscriptionService(
            model="whisper-small",
            base_url="http://127.0.0.1:8001/v1/audio",
            language="ko",
            urlopen_func=transport,
        )

        result = service.transcribe(
            SpeechSegment(
                raw_bytes=b"\x01\x02\x03\x04",
                start_ms=0,
                end_ms=1000,
            )
        )

        assert result.text == "안녕하세요"
        assert result.confidence == 0.93
        assert transport.last_request is not None
        assert transport.last_request.full_url == "http://127.0.0.1:8001/v1/audio/audio/transcriptions"
        body = transport.last_request.data
        assert b'name="model"' in body
        assert b'whisper-small' in body
        assert b'name="language"' in body
        assert b'filename="segment.wav"' in body
        assert b'RIFF' in body

    def test_json이_아니면_문자열_응답을_그대로_반환한다(self):
        transport = StubUrlopen(b"plain text result")
        service = OpenAICompatibleAudioTranscriptionService(
            model="whisper-small",
            base_url="http://127.0.0.1:8001/v1/audio",
            urlopen_func=transport,
        )

        result = service.transcribe(
            SpeechSegment(
                raw_bytes=b"\x01\x02",
                start_ms=0,
                end_ms=1000,
            )
        )

        assert result.text == "plain text result"
        assert result.confidence == 0.7


class StubUrlopen:
    """urllib.urlopen 대체용 테스트 스텁."""

    def __init__(self, response_payload: dict | bytes) -> None:
        self._response_payload = response_payload
        self.last_request = None

    def __call__(self, request, timeout=None):
        self.last_request = request
        return StubResponse(self._response_payload)


class StubResponse:
    """HTTP 응답 객체 스텁."""

    def __init__(self, response_payload: dict | bytes) -> None:
        self._response_payload = response_payload

    def __enter__(self) -> "StubResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        if isinstance(self._response_payload, bytes):
            return self._response_payload
        return json.dumps(self._response_payload).encode("utf-8")

