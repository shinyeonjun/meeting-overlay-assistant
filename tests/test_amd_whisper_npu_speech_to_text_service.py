"""AMD Whisper NPU STT 서비스 테스트."""

from __future__ import annotations

import numpy as np

import backend.app.services.audio.stt.amd_whisper_npu_speech_to_text_service as amd_whisper_module
from backend.app.services.audio.stt.amd_whisper_npu_speech_to_text_service import (
    AMDWhisperNPUConfig,
    AMDWhisperNPUSpeechToTextService,
)


class _FakeTokenizer:
    pad_token_id = 0
    eos_token_id = 99
    bos_token_id = 1

    def convert_tokens_to_ids(self, token: str) -> int:
        if token == "<|startoftranscript|>":
            return 11
        return -1

    def decode(self, token_ids: list[int], skip_special_tokens: bool = True) -> str:
        visible = [str(token_id) for token_id in token_ids if token_id not in {11, 21, 22, 23, 99, 0}]
        return " ".join(visible)


class _FakeProcessor:
    def __init__(self) -> None:
        self.tokenizer = _FakeTokenizer()

    def get_decoder_prompt_ids(self, language: str, task: str) -> list[tuple[int, int]]:
        assert language == "ko"
        assert task == "transcribe"
        return [(1, 21), (2, 22), (3, 23)]


class _FakeDecoderSession:
    def __init__(self, token_sequence: list[int], vocab_size: int = 128) -> None:
        self._token_sequence = token_sequence
        self._vocab_size = vocab_size
        self._calls = 0

    class _Input:
        shape = [1, 128]

    def get_inputs(self):
        return [self._Input()]

    def run(self, _output_names, inputs):
        token_buffer = inputs["x"]
        current_index = self._calls + 3
        next_token = self._token_sequence[self._calls]
        logits = np.full((1, token_buffer.shape[1], self._vocab_size), -10.0, dtype=np.float32)
        logits[0, current_index, next_token] = 10.0
        self._calls += 1
        return [logits]


class TestAMDWhisperNPUSpeechToTextService:
    """AMD Whisper NPU STT의 핵심 보조 로직을 검증한다."""

    def test_pcm16_bytes를_float32_오디오로_변환한다(self):
        service = AMDWhisperNPUSpeechToTextService(
            AMDWhisperNPUConfig(
                model_id="amd/whisper-small-onnx-npu",
                sample_rate_hz=16000,
                sample_width_bytes=2,
                channels=1,
            )
        )
        raw_bytes = np.asarray([0, 16384, -16384], dtype=np.int16).tobytes()

        audio = service._pcm16_to_float32_audio(raw_bytes)

        assert audio.dtype == np.float32
        assert np.allclose(audio, np.asarray([0.0, 0.5, -0.5], dtype=np.float32))

    def test_decoder_prompt를_기반으로_초기_token을_구성한다(self):
        service = AMDWhisperNPUSpeechToTextService(
            AMDWhisperNPUConfig(
                model_id="amd/whisper-small-onnx-npu",
                language="ko",
            )
        )

        initial_tokens = service._build_initial_tokens(_FakeProcessor())

        assert initial_tokens == [11, 21, 22, 23]

    def test_greedy_decode가_eos를_만날때까지_token을_생성한다(self):
        service = AMDWhisperNPUSpeechToTextService(
            AMDWhisperNPUConfig(
                model_id="amd/whisper-small-onnx-npu",
                language="ko",
                max_target_tokens=8,
            )
        )
        processor = _FakeProcessor()
        decoder_session = _FakeDecoderSession([5, 6, 99])
        encoder_hidden_states = np.zeros((1, 1500, 768), dtype=np.float32)

        token_ids, confidences = service._greedy_decode(
            decoder_session=decoder_session,
            encoder_hidden_states=encoder_hidden_states,
            processor=processor,
        )

        assert token_ids == [11, 21, 22, 23, 5, 6]
        assert len(confidences) == 2
        assert all(0.9 <= confidence <= 1.0 for confidence in confidences)

    def test_decoder_session_shape가_있으면_그_길이를_우선한다(self):
        service = AMDWhisperNPUSpeechToTextService(
            AMDWhisperNPUConfig(
                model_id="amd/whisper-small-onnx-npu",
                language="ko",
                max_target_tokens=32,
            )
        )

        assert service._resolve_decoder_sequence_length(_FakeDecoderSession([99])) == 128

    def test_model_id를_기반으로_cache_key를_구성한다(self):
        service = AMDWhisperNPUSpeechToTextService(
            AMDWhisperNPUConfig(model_id="amd/whisper-medium-onnx-npu")
        )

        assert service._build_cache_key("encoder") == "whisper_medium_encoder"

    def test_rms가_임계값보다_낮으면_무음으로_판정한다(self):
        service = AMDWhisperNPUSpeechToTextService(
            AMDWhisperNPUConfig(
                model_id="amd/whisper-small-onnx-npu",
                silence_rms_threshold=0.003,
            )
        )
        audio = np.zeros(16000, dtype=np.float32)

        assert service._compute_rms(audio) == 0.0

    def test_runtime_검증은_한번만_수행한다(self, monkeypatch):
        service = AMDWhisperNPUSpeechToTextService(
            AMDWhisperNPUConfig(model_id="amd/whisper-small-onnx-npu")
        )
        call_count = {"inspect": 0, "prepare": 0}

        class _RuntimeStatus:
            is_ready = True

        def fake_inspect_runtime(_installation_path):
            call_count["inspect"] += 1
            return _RuntimeStatus()

        def fake_prepare_runtime_environment():
            call_count["prepare"] += 1

        monkeypatch.setattr(amd_whisper_module, "inspect_runtime", fake_inspect_runtime)
        monkeypatch.setattr(service, "_prepare_runtime_environment", fake_prepare_runtime_environment)

        service._ensure_runtime_ready()
        service._ensure_runtime_ready()

        assert call_count == {"inspect": 1, "prepare": 1}

