"""OpenAI 호환 음성 전사 서버용 STT 구현."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from urllib import request
from uuid import uuid4

from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment
from server.app.services.audio.stt.transcription import SpeechToTextService, TranscriptionResult
from server.app.services.audio.io.wav_utils import wrap_pcm16_as_wav


class OpenAICompatibleAudioTranscriptionService(SpeechToTextService):
    """OpenAI 호환 audio transcription API를 호출한다."""

    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str | None = None,
        timeout_seconds: float = 20.0,
        language: str | None = "ko",
        sample_rate_hz: int = 16000,
        sample_width_bytes: int = 2,
        channels: int = 1,
        urlopen_func: Callable[..., Any] | None = None,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._language = language
        self._sample_rate_hz = sample_rate_hz
        self._sample_width_bytes = sample_width_bytes
        self._channels = channels
        self._urlopen = urlopen_func or request.urlopen

    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        """세그먼트 PCM 바이트를 WAV로 감싸 전사 서버에 보낸다."""
        wav_bytes = wrap_pcm16_as_wav(
            raw_bytes=segment.raw_bytes,
            sample_rate_hz=self._sample_rate_hz,
            sample_width_bytes=self._sample_width_bytes,
            channels=self._channels,
        )
        body, content_type = self._build_multipart_payload(wav_bytes)
        headers = {
            "Content-Type": content_type,
            "Accept": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        req = request.Request(
            url=f"{self._base_url}/audio/transcriptions",
            data=body,
            headers=headers,
            method="POST",
        )
        with self._urlopen(req, timeout=self._timeout_seconds) as response:
            response_bytes = response.read()

        text, confidence = self._parse_response(response_bytes)
        return TranscriptionResult(text=text, confidence=confidence)

    def _build_multipart_payload(self, wav_bytes: bytes) -> tuple[bytes, str]:
        boundary = f"----codex-boundary-{uuid4().hex}"
        fields = {
            "model": self._model,
            "response_format": "json",
        }
        if self._language:
            fields["language"] = self._language

        body = bytearray()
        for name, value in fields.items():
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode("utf-8")
            )

        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(b'Content-Disposition: form-data; name="file"; filename="segment.wav"\r\n')
        body.extend(b"Content-Type: audio/wav\r\n\r\n")
        body.extend(wav_bytes)
        body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))

        return bytes(body), f"multipart/form-data; boundary={boundary}"

    def _parse_response(self, response_bytes: bytes) -> tuple[str, float]:
        try:
            payload = json.loads(response_bytes.decode("utf-8"))
        except json.JSONDecodeError:
            return response_bytes.decode("utf-8", errors="ignore").strip(), 0.7

        text = payload.get("text", "")
        confidence = payload.get("confidence")
        if isinstance(confidence, (float, int)):
            return text, float(confidence)
        return text, 0.8 if text else 0.1

