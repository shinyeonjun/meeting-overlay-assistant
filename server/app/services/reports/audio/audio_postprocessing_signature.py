"""오디오 후처리 stage cache signature 생성 helper."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def build_stage_cache_signature_payload(
    *,
    service: object,
    audio_preprocessor: object,
    speaker_diarizer: object,
    speech_to_text_service: object,
    transcription_guard: object,
    expected_sample_rate_hz: int,
    expected_sample_width_bytes: int,
    expected_channels: int,
) -> str:
    """후처리 backend/config 조합을 안정적인 SHA-256 signature로 만든다."""

    payload = {
        "service": _qualified_type_name(service),
        "audio_preprocessor": _component_signature(audio_preprocessor),
        "speaker_diarizer": _component_signature(speaker_diarizer),
        "speech_to_text_service": _component_signature(speech_to_text_service),
        "transcription_guard": _component_signature(transcription_guard),
        "expected_sample_rate_hz": expected_sample_rate_hz,
        "expected_sample_width_bytes": expected_sample_width_bytes,
        "expected_channels": expected_channels,
    }
    encoded = json.dumps(
        _stable_json_value(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _component_signature(component: object) -> dict[str, Any]:
    config = getattr(component, "_config", None)
    payload: dict[str, Any] = {"type": _qualified_type_name(component)}
    if config is not None:
        payload["config"] = _stable_json_value(
            asdict(config) if is_dataclass(config) else config
        )
    return payload


def _qualified_type_name(value: object) -> str:
    value_type = type(value)
    return f"{value_type.__module__}.{value_type.__qualname__}"


def _stable_json_value(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value) and not isinstance(value, type):
        return _stable_json_value(asdict(value))
    if isinstance(value, dict):
        return {
            str(key): _stable_json_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_stable_json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)
