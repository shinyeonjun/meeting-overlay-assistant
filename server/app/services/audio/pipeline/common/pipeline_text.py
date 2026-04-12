"""오디오 파이프라인 텍스트/시간 유틸리티."""

from __future__ import annotations

import re
import time

from server.app.services.audio.stt.transcription import SpeechToTextService


def normalize_text(text: str) -> str:
    """비교용 텍스트를 정규화한다."""

    return re.sub(r"\s+", " ", text.casefold()).strip()


def compact_length(text: str) -> int:
    """공백과 기호를 제외한 길이를 계산한다."""

    return len(re.sub(r"[\W_]+", "", text, flags=re.UNICODE))


def now_ms() -> int:
    """현재 epoch millisecond를 반환한다."""

    return int(time.time() * 1000)


def resolve_stt_backend_name(speech_to_text_service: SpeechToTextService) -> str:
    """STT 백엔드 이름을 사람이 읽기 쉬운 문자열로 정리한다."""

    backend_name = getattr(speech_to_text_service, "backend_name", None)
    if isinstance(backend_name, str) and backend_name.strip():
        return backend_name.strip()
    return speech_to_text_service.__class__.__name__
