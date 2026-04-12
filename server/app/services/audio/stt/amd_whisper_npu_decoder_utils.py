"""오디오 영역의 amd whisper npu decoder utils 서비스를 제공한다."""
from __future__ import annotations

from typing import Any


def build_initial_tokens(*, processor: Any, language: str | None) -> list[int]:
    """Whisper decoder 프롬프트 토큰을 구성한다."""
    tokenizer = processor.tokenizer
    start_token_id = tokenizer.convert_tokens_to_ids("<|startoftranscript|>")
    if start_token_id is None or start_token_id < 0:
        start_token_id = tokenizer.bos_token_id
    if start_token_id is None:
        raise RuntimeError("Whisper tokenizer에서 start token을 찾지 못했습니다.")

    prompt_tokens = [int(start_token_id)]
    prompt_ids = processor.get_decoder_prompt_ids(
        language=language or "ko",
        task="transcribe",
    )
    prompt_tokens.extend(int(token_id) for _, token_id in prompt_ids)
    return prompt_tokens


def resolve_decoder_sequence_length(
    *,
    decoder_session: Any,
    configured_max_target_tokens: int,
    minimum_prompt_length: int = 0,
) -> int:
    """디코더 세션 shape 또는 설정값을 바탕으로 최대 시퀀스 길이를 정한다."""
    if hasattr(decoder_session, "get_inputs"):
        decoder_inputs = decoder_session.get_inputs()
        if decoder_inputs:
            shape = getattr(decoder_inputs[0], "shape", None)
            if isinstance(shape, (list, tuple)) and len(shape) >= 2 and isinstance(shape[1], int):
                return max(shape[1], minimum_prompt_length, 8)
    return max(configured_max_target_tokens, minimum_prompt_length, 8)


def softmax_confidence(*, logits, token_id: int, np_module: Any) -> float:
    """argmax 토큰의 softmax confidence를 계산한다."""
    shifted = logits - np_module.max(logits)
    exp_values = np_module.exp(shifted)
    probabilities = exp_values / np_module.sum(exp_values)
    return float(probabilities[token_id])


def greedy_decode(
    *,
    decoder_session: Any,
    encoder_hidden_states: Any,
    processor: Any,
    language: str | None,
    configured_max_target_tokens: int,
    np_module: Any,
) -> tuple[list[int], list[float]]:
    """Whisper decoder를 greedy 방식으로 실행한다."""
    tokenizer = processor.tokenizer
    initial_tokens = build_initial_tokens(
        processor=processor,
        language=language,
    )
    max_target_tokens = resolve_decoder_sequence_length(
        decoder_session=decoder_session,
        configured_max_target_tokens=configured_max_target_tokens,
        minimum_prompt_length=len(initial_tokens),
    )
    if len(initial_tokens) >= max_target_tokens:
        return initial_tokens[:max_target_tokens], []

    pad_token_id = tokenizer.pad_token_id
    if pad_token_id is None:
        pad_token_id = tokenizer.eos_token_id
    if pad_token_id is None:
        pad_token_id = 0

    token_buffer = np_module.full((1, max_target_tokens), pad_token_id, dtype=np_module.int64)
    token_buffer[0, : len(initial_tokens)] = np_module.asarray(initial_tokens, dtype=np_module.int64)

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
        next_token_confidence = softmax_confidence(
            logits=next_token_logits,
            token_id=next_token_id,
            np_module=np_module,
        )
        token_buffer[0, current_length] = next_token_id
        current_length += 1

        if eos_token_id is not None and next_token_id == eos_token_id:
            break

        generated_tokens.append(next_token_id)
        confidences.append(next_token_confidence)

    return initial_tokens + generated_tokens, confidences
