"""오디오 영역의 compat 서비스를 제공한다."""
from __future__ import annotations

from server.app.services.audio.stt.factory_builders.compat_helpers import (
    build_amd_whisper_npu_compat,
    build_faster_whisper_compat,
    build_faster_whisper_streaming_compat,
    build_moonshine_compat,
    build_moonshine_streaming_compat,
    build_openai_compatible_audio_compat,
    build_placeholder_compat,
    build_sherpa_onnx_streaming_compat,
)

__all__ = [
    "build_amd_whisper_npu_compat",
    "build_faster_whisper_compat",
    "build_faster_whisper_streaming_compat",
    "build_moonshine_compat",
    "build_moonshine_streaming_compat",
    "build_openai_compatible_audio_compat",
    "build_placeholder_compat",
    "build_sherpa_onnx_streaming_compat",
]
