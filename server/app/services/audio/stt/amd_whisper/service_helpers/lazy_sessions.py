"""AMD Whisper lazy session loader."""

from __future__ import annotations


def get_processor(*, service):
    """Whisper processor를 lazy하게 준비한다."""

    if service._processor is None:
        whisper_processor = service._whisper_processor()
        service._processor = whisper_processor.from_pretrained(service._resolve_base_model_id())
    return service._processor


def get_encoder_session(*, service):
    """Encoder ONNX session을 lazy하게 준비한다."""

    if service._encoder_session is None:
        ort = service._onnxruntime()
        service._encoder_session = ort.InferenceSession(
            str(service._config.encoder_model_path),
            providers=["VitisAIExecutionProvider", "CPUExecutionProvider"],
            provider_options=[service._build_vitis_provider_options("encoder"), {}],
        )
    return service._encoder_session


def get_decoder_session(*, service):
    """Decoder ONNX session을 lazy하게 준비한다."""

    if service._decoder_session is None:
        ort = service._onnxruntime()
        service._decoder_session = ort.InferenceSession(
            str(service._config.decoder_model_path),
            providers=["VitisAIExecutionProvider", "CPUExecutionProvider"],
            provider_options=[service._build_vitis_provider_options("decoder"), {}],
        )
    return service._decoder_session
