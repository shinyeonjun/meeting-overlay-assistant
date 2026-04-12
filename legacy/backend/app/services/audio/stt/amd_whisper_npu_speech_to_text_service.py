"""AMD Whisper NPU STT 구현체."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.app.services.audio.stt.amd_whisper_artifacts import AMDWhisperArtifacts
from backend.app.services.audio.stt.ryzenai_runtime import (
    build_runtime_error_message,
    inspect_runtime,
)
from backend.app.services.audio.segmentation.speech_segmenter import SpeechSegment
from backend.app.services.audio.stt.transcription import SpeechToTextService, TranscriptionResult


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

    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        """PCM16 세그먼트를 Whisper encoder/decoder로 전사한다."""
        self._ensure_runtime_ready()
        self._ensure_artifacts_ready()

        audio = self._pcm16_to_float32_audio(segment.raw_bytes)
        if audio.size == 0:
            logger.debug("STT 입력이 비어 있음")
            return TranscriptionResult(text="", confidence=0.0)

        audio_rms = self._compute_rms(audio)
        if audio_rms < self._config.silence_rms_threshold:
            logger.debug(
                "STT 무음 구간 스킵: rms=%.6f threshold=%.6f",
                audio_rms,
                self._config.silence_rms_threshold,
            )
            return TranscriptionResult(text="", confidence=0.0)

        processor = self._get_processor()
        encoder_session = self._get_encoder_session()
        decoder_session = self._get_decoder_session()

        input_features = processor(
            audio=audio,
            sampling_rate=self._config.sample_rate_hz,
            return_tensors="np",
        ).input_features
        input_features = input_features.astype(self._np().float32, copy=False)
        encoder_hidden_states = encoder_session.run(None, {"x": input_features})[0]
        encoder_hidden_states = encoder_hidden_states.astype(self._np().float32, copy=False)

        decoded_token_ids, confidences = self._greedy_decode(
            decoder_session=decoder_session,
            encoder_hidden_states=encoder_hidden_states,
            processor=processor,
        )
        text = processor.tokenizer.decode(decoded_token_ids, skip_special_tokens=True).strip()
        result = TranscriptionResult(
            text=text,
            confidence=self._average_confidence(confidences, text),
        )
        logger.debug(
            "STT 전사 완료: text=%s confidence=%.4f",
            result.text,
            result.confidence,
        )
        return result

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
        logger.info("AMD Whisper NPU 런타임 준비 완료: model_id=%s", self._config.model_id)

    def _ensure_artifacts_ready(self) -> None:
        if self._artifacts_validated:
            return

        missing_paths = self._artifacts.missing_paths()
        if missing_paths:
            raise RuntimeError(
                "amd_whisper_npu backend를 실행하려면 Whisper ONNX 아티팩트가 필요합니다. "
                f"비어있는 설정: {', '.join(missing_paths)}"
            )
        self._artifacts_validated = True
        logger.info("AMD Whisper 아티팩트 검증 완료: model_id=%s", self._config.model_id)

    def _pcm16_to_float32_audio(self, raw_bytes: bytes):
        np = self._np()
        if not raw_bytes:
            return np.asarray([], dtype=np.float32)

        frame_size = max(self._config.sample_width_bytes * self._config.channels, 1)
        aligned_size = len(raw_bytes) - (len(raw_bytes) % frame_size)
        if aligned_size <= 0:
            return np.asarray([], dtype=np.float32)

        if self._config.sample_width_bytes != 2:
            raise RuntimeError("amd_whisper_npu backend는 현재 16-bit PCM 입력만 지원합니다.")

        pcm = np.frombuffer(raw_bytes[:aligned_size], dtype=np.int16).astype(np.float32)
        if self._config.channels > 1:
            pcm = pcm.reshape(-1, self._config.channels).mean(axis=1)
        return np.clip(pcm / 32768.0, -1.0, 1.0)

    def _get_processor(self):
        if self._processor is None:
            whisper_processor = self._whisper_processor()
            self._processor = whisper_processor.from_pretrained(self._resolve_base_model_id())
        return self._processor

    def _get_encoder_session(self):
        if self._encoder_session is None:
            ort = self._onnxruntime()
            self._encoder_session = ort.InferenceSession(
                str(self._config.encoder_model_path),
                providers=["VitisAIExecutionProvider", "CPUExecutionProvider"],
                provider_options=[self._build_vitis_provider_options("encoder"), {}],
            )
        return self._encoder_session

    def _get_decoder_session(self):
        if self._decoder_session is None:
            ort = self._onnxruntime()
            self._decoder_session = ort.InferenceSession(
                str(self._config.decoder_model_path),
                providers=["VitisAIExecutionProvider", "CPUExecutionProvider"],
                provider_options=[self._build_vitis_provider_options("decoder"), {}],
            )
        return self._decoder_session

    def _greedy_decode(self, decoder_session: Any, encoder_hidden_states: Any, processor: Any):
        np = self._np()
        tokenizer = processor.tokenizer
        max_target_tokens = self._resolve_decoder_sequence_length(decoder_session)
        initial_tokens = self._build_initial_tokens(processor)
        if len(initial_tokens) >= max_target_tokens:
            return initial_tokens[:max_target_tokens], []

        pad_token_id = tokenizer.pad_token_id
        if pad_token_id is None:
            pad_token_id = tokenizer.eos_token_id
        if pad_token_id is None:
            pad_token_id = 0

        token_buffer = np.full((1, max_target_tokens), pad_token_id, dtype=np.int64)
        token_buffer[0, : len(initial_tokens)] = np.asarray(initial_tokens, dtype=np.int64)

        eos_token_id = tokenizer.eos_token_id
        generated_tokens: list[int] = []
        confidences: list[float] = []
        current_length = len(initial_tokens)

        while current_length < max_target_tokens:
            logits = decoder_session.run(
                None,
                {
                    "x": token_buffer,
                    "xa": encoder_hidden_states,
                },
            )[0]
            next_token_logits = logits[0, current_length - 1]
            next_token_id = int(next_token_logits.argmax())
            next_token_confidence = self._softmax_confidence(next_token_logits, next_token_id)
            token_buffer[0, current_length] = next_token_id
            current_length += 1

            if eos_token_id is not None and next_token_id == eos_token_id:
                break

            generated_tokens.append(next_token_id)
            confidences.append(next_token_confidence)

        return initial_tokens + generated_tokens, confidences

    def _build_initial_tokens(self, processor: Any) -> list[int]:
        tokenizer = processor.tokenizer
        start_token_id = tokenizer.convert_tokens_to_ids("<|startoftranscript|>")
        if start_token_id is None or start_token_id < 0:
            start_token_id = tokenizer.bos_token_id
        if start_token_id is None:
            raise RuntimeError("Whisper tokenizer에서 start token을 찾지 못했습니다.")

        prompt_tokens = [int(start_token_id)]
        prompt_ids = processor.get_decoder_prompt_ids(
            language=self._config.language or "ko",
            task="transcribe",
        )
        prompt_tokens.extend(int(token_id) for _, token_id in prompt_ids)
        return prompt_tokens

    def _resolve_decoder_sequence_length(self, decoder_session: Any) -> int:
        if hasattr(decoder_session, "get_inputs"):
            decoder_inputs = decoder_session.get_inputs()
            if decoder_inputs:
                shape = getattr(decoder_inputs[0], "shape", None)
                if isinstance(shape, (list, tuple)) and len(shape) >= 2 and isinstance(shape[1], int):
                    return max(shape[1], len(self._build_initial_tokens(self._get_processor())), 8)
        return max(self._config.max_target_tokens, 8)

    def _build_vitis_provider_options(self, component: str) -> dict[str, str]:
        config_path = self._resolve_component_config_path(component)
        if config_path is None:
            return {}

        cache_dir = self._resolve_cache_dir()
        return {
            "config_file": str(config_path),
            "cache_dir": str(cache_dir),
            "cache_key": self._build_cache_key(component),
        }

    def _prepare_runtime_environment(self) -> None:
        installation_path = self._config.installation_path
        if installation_path is None or os.name != "nt":
            return

        candidate_dirs = [
            installation_path / "deployment",
            installation_path / "onnxruntime" / "bin",
            installation_path / "voe-4.0-win_amd64",
        ]
        existing_dirs = [path for path in candidate_dirs if path.exists()]
        for path in existing_dirs:
            path_str = str(path)
            if path_str not in os.environ.get("PATH", ""):
                os.environ["PATH"] = f"{path_str};{os.environ.get('PATH', '')}"
            if hasattr(os, "add_dll_directory"):
                handle = os.add_dll_directory(path_str)
                self._dll_directory_handles.append(handle)

    def _resolve_component_config_path(self, component: str) -> Path | None:
        config_root = self._project_root() / "backend" / "models" / "stt" / "config"
        config_name = f"vitisai_config_whisper_{component}.json"
        config_path = config_root / config_name
        if config_path.exists():
            return config_path
        return None

    def _resolve_cache_dir(self) -> Path:
        cache_dir = self._project_root() / "backend" / "models" / "stt" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def _build_cache_key(self, component: str) -> str:
        model_key = self._resolve_model_key()
        return f"whisper_{model_key}_{component}"

    def _resolve_model_key(self) -> str:
        model_id = self._config.model_id.lower()
        if "large-v3-turbo" in model_id or "large-turbo" in model_id:
            return "large_turbo"
        if "large-v3" in model_id:
            return "large_v3"
        if "medium" in model_id:
            return "medium"
        if "base" in model_id:
            return "base"
        return "small"

    def _resolve_base_model_id(self) -> str:
        if self._config.base_model_id:
            return self._config.base_model_id

        model_id = self._config.model_id.lower()
        if "large-v3-turbo" in model_id or "large-turbo" in model_id:
            return "openai/whisper-large-v3-turbo"
        if "large-v3" in model_id:
            return "openai/whisper-large-v3"
        if "medium" in model_id:
            return "openai/whisper-medium"
        if "base" in model_id:
            return "openai/whisper-base"
        return "openai/whisper-small"

    def _average_confidence(self, confidences: list[float], text: str) -> float:
        if confidences:
            return round(sum(confidences) / len(confidences), 4)
        return 0.8 if text else 0.0

    def _compute_rms(self, audio) -> float:
        np = self._np()
        if audio.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(np.square(audio, dtype=np.float32))))

    def _softmax_confidence(self, logits, token_id: int) -> float:
        np = self._np()
        shifted = logits - np.max(logits)
        exp_values = np.exp(shifted)
        probabilities = exp_values / np.sum(exp_values)
        return float(probabilities[token_id])

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
        return Path(__file__).resolve().parents[4]

