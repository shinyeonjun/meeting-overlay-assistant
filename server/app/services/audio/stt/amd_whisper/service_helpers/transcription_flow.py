"""오디오 영역의 transcription flow 서비스를 제공한다."""
from __future__ import annotations


def transcribe_segment(*, service, segment, transcription_result_cls):
    """세그먼트를 AMD Whisper NPU로 전사한다."""

    service._ensure_runtime_ready()
    service._ensure_artifacts_ready()

    audio = service._pcm16_to_float32_audio(segment.raw_bytes)
    if audio.size == 0:
        service._logger.debug("STT 입력이 비어 있음")
        return transcription_result_cls(text="", confidence=0.0)

    audio_rms = service._compute_rms(audio)
    if audio_rms < service._config.silence_rms_threshold:
        service._logger.debug(
            "STT 무음 구간 스킵: rms=%.6f threshold=%.6f",
            audio_rms,
            service._config.silence_rms_threshold,
        )
        return transcription_result_cls(text="", confidence=0.0)

    processor = service._get_processor()
    input_features = processor(
        audio=audio,
        sampling_rate=service._config.sample_rate_hz,
        return_tensors="np",
    ).input_features

    np_module = service._np()
    input_features = input_features.astype(np_module.float32, copy=False)
    encoder_hidden_states = service._get_encoder_session().run(None, {"x": input_features})[0]
    encoder_hidden_states = encoder_hidden_states.astype(np_module.float32, copy=False)

    decoded_token_ids, confidences = service._greedy_decode(
        decoder_session=service._get_decoder_session(),
        encoder_hidden_states=encoder_hidden_states,
        processor=processor,
    )
    text = processor.tokenizer.decode(decoded_token_ids, skip_special_tokens=True).strip()
    result = transcription_result_cls(
        text=text,
        confidence=service._average_confidence(confidences, text),
    )
    service._logger.debug(
        "STT 전사 완료: text=%s confidence=%.4f",
        result.text,
        result.confidence,
    )
    return result
