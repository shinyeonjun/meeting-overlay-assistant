"""오디오 영역의 recognizer 서비스를 제공한다."""
from __future__ import annotations


def create_online_recognizer(*, config, resolve_transducer_artifacts):
    """sherpa-onnx OnlineRecognizer를 생성한다."""

    try:
        import sherpa_onnx
    except ImportError as error:  # pragma: no cover - 선택 의존성
        raise RuntimeError(
            "sherpa_onnx_streaming backend를 사용하려면 sherpa-onnx 패키지가 필요합니다."
        ) from error

    artifacts = resolve_transducer_artifacts(config.model_path)
    return sherpa_onnx.OnlineRecognizer.from_transducer(
        tokens=str(artifacts["tokens"]),
        encoder=str(artifacts["encoder"]),
        decoder=str(artifacts["decoder"]),
        joiner=str(artifacts["joiner"]),
        num_threads=config.num_threads,
        sample_rate=config.sample_rate_hz,
        provider=config.provider,
        decoding_method=config.decoding_method,
        max_active_paths=config.max_active_paths,
        enable_endpoint_detection=config.enable_endpoint_detection,
        rule1_min_trailing_silence=config.rule1_min_trailing_silence,
        rule2_min_trailing_silence=config.rule2_min_trailing_silence,
        rule3_min_utterance_length=config.rule3_min_utterance_length,
    )
