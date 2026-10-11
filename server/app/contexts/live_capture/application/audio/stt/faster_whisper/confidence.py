"""faster-whisper confidence 계산 유틸리티."""

from __future__ import annotations

import math
from typing import Any


def average_confidence(*, segments: list[Any], text: str) -> float:
    """segment avg_logprob 기준 평균 confidence를 계산한다."""

    avg_logprobs = [
        float(segment.avg_logprob)
        for segment in segments
        if getattr(segment, "avg_logprob", None) is not None
    ]
    if not avg_logprobs:
        return 0.8 if text else 0.0
    probabilities = [min(max(math.exp(value), 0.0), 1.0) for value in avg_logprobs]
    return round(sum(probabilities) / len(probabilities), 4)


def max_no_speech_prob(*, segments: list[Any]) -> float | None:
    """segment no_speech_prob 최대값을 반환한다."""

    probabilities = [
        float(segment.no_speech_prob)
        for segment in segments
        if getattr(segment, "no_speech_prob", None) is not None
    ]
    if not probabilities:
        return None
    return round(max(probabilities), 4)
