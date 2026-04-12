"""오디오 영역의 amd whisper npu speech to text service 서비스를 제공한다."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment
from server.app.services.audio.stt.amd_whisper.decode import average_confidence
from server.app.services.audio.stt.amd_whisper.service_helpers import (
    ensure_artifacts_ready,
    get_decoder_session,
    get_encoder_session,
    get_processor,
    transcribe_segment,
)
from server.app.services.audio.stt.amd_whisper_artifacts import AMDWhisperArtifacts
from server.app.services.audio.stt.amd_whisper_npu_audio_utils import (
    compute_rms,
    pcm16_to_float32_audio,
)
from server.app.services.audio.stt.amd_whisper_npu_decoder_utils import (
    build_initial_tokens,
    greedy_decode,
    resolve_decoder_sequence_length,
    softmax_confidence,
)
from server.app.services.audio.stt.amd_whisper_npu_runtime import AMDWhisperNPURuntimeHelper
from server.app.services.audio.stt.ryzenai_runtime import (
    build_runtime_error_message,
    inspect_runtime,
)
from server.app.services.audio.stt.transcription import SpeechToTextService, TranscriptionResult


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AMDWhisperNPUConfig:
    """AMD Whisper NPU 실행 설정."""

    model_id: str
    model_path: Path | None = None
    installation_path: Path | None = None
    encoder_model_path: Path | None = None
    decoder_model_path: Path | None = None
    encoder_rai_path: Path | None = None
    base_model_id: str | None = None
    language: str | None = "ko"
    sample_rate_hz: int = 16000
    sample_width_bytes: int = 2
    channels: int = 1
    max_target_tokens: int = 128
    silence_rms_threshold: float = 0.003


class AMDWhisperNPUSpeechToTextService(SpeechToTextService):
    """AMD Ryzen AI NPU에서 Whisper encoder를 실행하는 STT 서비스."""

    def __init__(self, config: AMDWhisperNPUConfig) -> None:
        self._config = config
        self._processor: Any | None = None
        self._encoder_session: Any | None = None
        self._decoder_session: Any | None = None
        self._dll_directory_handles: list[Any] = []
        self._runtime_validated = False
        self._artifacts_validated = False
        self._artifacts = AMDWhisperArtifacts(
            encoder_model_path=config.encoder_model_path,
            decoder_model_path=config.decoder_model_path,
            encoder_rai_path=config.encoder_rai_path,
        )
        self._runtime_helper = AMDWhisperNPURuntimeHelper(
            model_id=config.model_id,
            installation_path=config.installation_path,
            base_model_id=config.base_model_id,
            project_root=self._project_root(),
        )
        self._logger = logger

    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        """PCM16 세그먼트를 Whisper encoder/decoder로 전사한다."""

        return transcribe_segment(
            service=self,
            segment=segment,
            transcription_result_cls=TranscriptionResult,
        )

    def _ensure_runtime_ready(self) -> None:
        if self._runtime_validated:
            return

        runtime_status = inspect_runtime(
            str(self._config.installation_path) if self._config.installation_path else None
        )
        if not runtime_status.is_ready:
            raise RuntimeError(build_runtime_error_message(runtime_status))

        self._prepare_runtime_environment()
        self._runtime_validated = True
        self._logger.info("AMD Whisper NPU 런타임 준비 완료: model_id=%s", self._config.model_id)

    def _ensure_artifacts_ready(self) -> None:
        ensure_artifacts_ready(service=self)

    def _pcm16_to_float32_audio(self, raw_bytes: bytes):
        return pcm16_to_float32_audio(
            raw_bytes=raw_bytes,
            sample_width_bytes=self._config.sample_width_bytes,
            channels=self._config.channels,
            backend_name="amd_whisper_npu",
            np_module=self._np(),
        )

    def _get_processor(self):
        return get_processor(service=self)

    def _get_encoder_session(self):
        return get_encoder_session(service=self)

    def _get_decoder_session(self):
        return get_decoder_session(service=self)

    def _greedy_decode(self, decoder_session: Any, encoder_hidden_states: Any, processor: Any):
        return greedy_decode(
            decoder_session=decoder_session,
            encoder_hidden_states=encoder_hidden_states,
            processor=processor,
            language=self._config.language,
            configured_max_target_tokens=self._config.max_target_tokens,
            np_module=self._np(),
        )

    def _build_initial_tokens(self, processor: Any) -> list[int]:
        return build_initial_tokens(
            processor=processor,
            language=self._config.language,
        )

    def _resolve_decoder_sequence_length(self, decoder_session: Any) -> int:
        initial_token_count = 0
        try:
            initial_token_count = len(self._build_initial_tokens(self._get_processor()))
        except Exception:
            initial_token_count = 0

        return resolve_decoder_sequence_length(
            decoder_session=decoder_session,
            configured_max_target_tokens=self._config.max_target_tokens,
            minimum_prompt_length=initial_token_count,
        )

    def _build_vitis_provider_options(self, component: str) -> dict[str, str]:
        return self._runtime_helper.build_vitis_provider_options(component)

    def _prepare_runtime_environment(self) -> None:
        self._runtime_helper.prepare_runtime_environment(self._dll_directory_handles)

    def _resolve_component_config_path(self, component: str) -> Path | None:
        return self._runtime_helper.resolve_component_config_path(component)

    def _resolve_cache_dir(self) -> Path:
        return self._runtime_helper.resolve_cache_dir()

    def _build_cache_key(self, component: str) -> str:
        return self._runtime_helper.build_cache_key(component)

    def _resolve_model_key(self) -> str:
        return self._runtime_helper.resolve_model_key()

    def _resolve_base_model_id(self) -> str:
        return self._runtime_helper.resolve_base_model_id()

    def _average_confidence(self, confidences: list[float], text: str) -> float:
        return average_confidence(confidences=confidences, text=text)

    def _compute_rms(self, audio) -> float:
        return compute_rms(
            audio,
            np_module=self._np(),
        )

    def _softmax_confidence(self, logits, token_id: int) -> float:
        return softmax_confidence(
            logits=logits,
            token_id=token_id,
            np_module=self._np(),
        )

    @staticmethod
    def _np():
        import numpy as np

        return np

    @staticmethod
    def _onnxruntime():
        import onnxruntime as ort

        return ort

    @staticmethod
    def _whisper_processor():
        from transformers import WhisperProcessor

        return WhisperProcessor

    @staticmethod
    def _project_root() -> Path:
        return Path(__file__).resolve().parents[5]
