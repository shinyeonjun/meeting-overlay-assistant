"""공통 영역의 question lane filter 서비스를 제공한다."""
from __future__ import annotations

import re
from dataclasses import dataclass

from server.app.services.live_questions.models import LiveQuestionUtterance

_WHITESPACE_RE = re.compile(r"\s+")
_PUNCTUATION_RE = re.compile(r"[^\w가-힣]+")

_FILLER_TEXTS = frozenset(
    {
        "어",
        "음",
        "아",
        "어어",
        "음음",
        "그",
        "그냥",
        "저기",
        "잠깐",
    }
)

_TRAILING_TEXTS = frozenset(
    {
        "네",
        "예",
        "맞아요",
        "맞습니다",
        "좋아요",
        "알겠습니다",
        "오케이",
        "확인했습니다",
    }
)

_QUESTION_HINTS = (
    "뭐",
    "왜",
    "어떻게",
    "언제",
    "어디",
    "누가",
    "가능",
    "되나요",
    "할까요",
    "맞나요",
    "인가요",
    "일까요",
    "일지",
    "?",
)


@dataclass(frozen=True, slots=True)
class QuestionLaneFilterDecision:
    """공통 영역의 QuestionLaneFilterDecision 행위를 담당한다."""
    keep: bool
    reason: str | None = None


class QuestionLaneFilter:
    """질문 lane 입력을 가볍게 정제한다."""

    def __init__(
        self,
        *,
        min_compact_chars: int = 6,
        min_word_count: int = 3,
        max_window_size: int = 2,
    ) -> None:
        self._min_compact_chars = max(min_compact_chars, 1)
        self._min_word_count = max(min_word_count, 1)
        self._max_window_size = max(max_window_size, 1)

    def decide(self, utterance: LiveQuestionUtterance) -> QuestionLaneFilterDecision:
        """질문 분석 대상으로 유지할지 결정한다."""

        text = _normalize_text(utterance.text)
        if not text:
            return QuestionLaneFilterDecision(False, "empty")

        compact = _compact_text(text)
        if compact in _FILLER_TEXTS:
            return QuestionLaneFilterDecision(False, "filler_only")

        if compact in _TRAILING_TEXTS:
            return QuestionLaneFilterDecision(False, "tail_only")

        word_count = len([token for token in text.split(" ") if token])
        has_question_hint = any(token in text for token in _QUESTION_HINTS)
        if (
            len(compact) < self._min_compact_chars
            and word_count < self._min_word_count
            and not has_question_hint
        ):
            return QuestionLaneFilterDecision(False, "too_short")

        return QuestionLaneFilterDecision(True)

    def select_window(
        self,
        utterances: list[LiveQuestionUtterance],
    ) -> list[LiveQuestionUtterance]:
        """질문 분석에 넘길 짧은 윈도우만 남긴다."""

        if not utterances:
            return []

        selected = list(utterances[-self._max_window_size :])
        if len(selected) == 1:
            return selected

        if any(self._looks_like_question(item.text) for item in selected):
            return selected

        return [selected[-1]]

    def _looks_like_question(self, text: str) -> bool:
        normalized = _normalize_text(text)
        return any(token in normalized for token in _QUESTION_HINTS)


def _normalize_text(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", (text or "").strip())


def _compact_text(text: str) -> str:
    cleaned = _PUNCTUATION_RE.sub("", text or "")
    return cleaned.replace(" ", "")
