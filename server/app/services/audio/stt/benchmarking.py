"""STT 벤치마크 계산 유틸리티."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorRateResult:
    """오차율 계산 결과."""

    distance: int
    reference_length: int
    rate: float


@dataclass(frozen=True)
class GuardPassStats:
    """전사 가드 통과 통계."""

    raw_segment_count: int
    non_empty_segment_count: int
    kept_segment_count: int

    @property
    def non_empty_rate(self) -> float:
        if self.raw_segment_count == 0:
            return 0.0
        return self.non_empty_segment_count / self.raw_segment_count

    @property
    def keep_rate_vs_raw(self) -> float:
        if self.raw_segment_count == 0:
            return 0.0
        return self.kept_segment_count / self.raw_segment_count

    @property
    def keep_rate_vs_non_empty(self) -> float:
        if self.non_empty_segment_count == 0:
            return 0.0
        return self.kept_segment_count / self.non_empty_segment_count


def compute_word_error_rate(reference_text: str, hypothesis_text: str) -> ErrorRateResult:
    """단어 기준 WER를 계산한다."""
    reference_tokens = _normalize_words(reference_text)
    hypothesis_tokens = _normalize_words(hypothesis_text)
    return _build_error_rate(reference_tokens, hypothesis_tokens)


def compute_character_error_rate(reference_text: str, hypothesis_text: str) -> ErrorRateResult:
    """문자 기준 CER를 계산한다."""
    reference_tokens = list(_normalize_characters(reference_text))
    hypothesis_tokens = list(_normalize_characters(hypothesis_text))
    return _build_error_rate(reference_tokens, hypothesis_tokens)


def _build_error_rate(reference_tokens: list[str], hypothesis_tokens: list[str]) -> ErrorRateResult:
    reference_length = len(reference_tokens)
    distance = _levenshtein_distance(reference_tokens, hypothesis_tokens)
    rate = distance / reference_length if reference_length > 0 else 0.0
    return ErrorRateResult(
        distance=distance,
        reference_length=reference_length,
        rate=round(rate, 4),
    )


def _normalize_words(text: str) -> list[str]:
    return [token for token in text.strip().split() if token]


def _normalize_characters(text: str) -> str:
    return "".join(text.split())


def _levenshtein_distance(reference_tokens: list[str], hypothesis_tokens: list[str]) -> int:
    if not reference_tokens:
        return len(hypothesis_tokens)
    if not hypothesis_tokens:
        return len(reference_tokens)

    previous_row = list(range(len(hypothesis_tokens) + 1))
    for reference_index, reference_token in enumerate(reference_tokens, start=1):
        current_row = [reference_index]
        for hypothesis_index, hypothesis_token in enumerate(hypothesis_tokens, start=1):
            substitution_cost = 0 if reference_token == hypothesis_token else 1
            current_row.append(
                min(
                    previous_row[hypothesis_index] + 1,
                    current_row[hypothesis_index - 1] + 1,
                    previous_row[hypothesis_index - 1] + substitution_cost,
                )
            )
        previous_row = current_row
    return previous_row[-1]
