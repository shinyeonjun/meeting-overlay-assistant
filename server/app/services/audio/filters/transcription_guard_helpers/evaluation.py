"""오디오 영역의 evaluation 서비스를 제공한다."""
from __future__ import annotations

import re


def normalize_text(text: str) -> str:
    """공백을 정규화한 텍스트를 반환한다."""

    return " ".join(text.split())


def is_boundary_only(*, boundary_only_pattern, text: str) -> bool:
    """boundary term만 있는지 확인한다."""

    return bool(boundary_only_pattern.fullmatch(text))


def contains_blocked_phrase(*, config, blocked_patterns, text: str, confidence: float) -> bool:
    """차단 phrase/pattern 포함 여부를 확인한다."""

    if confidence > config.blocked_phrase_max_confidence:
        return False

    normalized = text.casefold()
    if any(
        blocked_phrase.casefold() in normalized
        for blocked_phrase in config.blocked_phrases
    ):
        return True
    return any(pattern.search(text) for pattern in blocked_patterns)


def is_high_no_speech_prob(*, config, result) -> bool:
    """no-speech probability가 임계치를 넘는지 확인한다."""

    if config.max_no_speech_prob is None:
        return False
    if result.no_speech_prob is None:
        return False
    return result.no_speech_prob > config.max_no_speech_prob


def is_too_short_for_confidence(*, config, text: str, confidence: float) -> bool:
    """짧은 텍스트가 confidence 조건을 통과하는지 확인한다."""

    compact = re.sub(r"[\W_]+", "", text, flags=re.UNICODE)
    if len(compact) > config.min_compact_length:
        return False
    return confidence < config.short_text_min_confidence


def looks_repetitive(*, config, token_split_pattern, text: str) -> bool:
    """반복 어절/문장 패턴인지 확인한다."""

    tokens = [token for token in token_split_pattern.split(text) if token]
    if len(tokens) < config.min_repetition_tokens:
        return False

    token_counts: dict[str, int] = {}
    max_count = 0
    max_consecutive = 1
    current_consecutive = 1

    for index, token in enumerate(tokens):
        token_counts[token] = token_counts.get(token, 0) + 1
        max_count = max(max_count, token_counts[token])
        if index > 0 and token == tokens[index - 1]:
            current_consecutive += 1
            max_consecutive = max(max_consecutive, current_consecutive)
        else:
            current_consecutive = 1

    repeat_ratio = max_count / len(tokens)
    return (
        repeat_ratio >= config.max_repeat_ratio
        or max_consecutive >= config.max_consecutive_repeat
    )


def is_language_inconsistent(*, config, text: str, confidence: float) -> bool:
    """언어 스크립트 일관성이 깨졌는지 확인한다."""

    if not config.language_consistency_enabled:
        return False
    if not config.expected_language:
        return False
    if confidence > config.language_consistency_max_confidence:
        return False

    expected_language = config.expected_language.casefold()
    script_counts = _count_scripts(text)
    total_letter_count = sum(script_counts.values())
    if total_letter_count == 0:
        return False

    compact = re.sub(r"\s+", "", text)
    letter_ratio = total_letter_count / max(len(compact), 1)
    if letter_ratio < config.min_letter_ratio:
        return True

    target_count = _select_target_script_count(expected_language, script_counts)
    target_ratio = target_count / total_letter_count
    if target_count == 0:
        return True
    return target_ratio < config.min_target_script_ratio


def compile_boundary_pattern(boundary_terms: tuple[str, ...]) -> re.Pattern[str]:
    """boundary term 전용 정규식을 만든다."""

    escaped_terms = "|".join(re.escape(term) for term in boundary_terms)
    return re.compile(
        rf"^[\s\[\]\(\)\-_.~]*({escaped_terms})[\s\[\]\(\)\-_.~]*$"
    )


def _count_scripts(text: str) -> dict[str, int]:
    counts = {
        "hangul": 0,
        "latin": 0,
        "japanese": 0,
    }
    for char in text:
        code = ord(char)
        if 0xAC00 <= code <= 0xD7A3 or 0x3131 <= code <= 0x318E:
            counts["hangul"] += 1
        elif (0x3040 <= code <= 0x30FF) or (0x4E00 <= code <= 0x9FFF):
            counts["japanese"] += 1
        elif ("A" <= char <= "Z") or ("a" <= char <= "z"):
            counts["latin"] += 1
    return counts


def _select_target_script_count(
    expected_language: str,
    script_counts: dict[str, int],
) -> int:
    if expected_language.startswith("ko"):
        return script_counts["hangul"]
    if expected_language.startswith("en"):
        return script_counts["latin"]
    if expected_language.startswith("ja"):
        return script_counts["japanese"]
    return sum(script_counts.values())
