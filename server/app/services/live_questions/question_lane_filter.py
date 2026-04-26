"""실시간 질문 lane에 보낼 발화 window를 가볍게 거른다."""

from __future__ import annotations

import re
from dataclasses import dataclass

from server.app.services.live_questions.models import LiveQuestionUtterance

_WHITESPACE_RE = re.compile(r"\s+")
_PUNCTUATION_RE = re.compile(r"[^\w가-힣]+", re.UNICODE)
_QUESTION_MARK_RE = re.compile(r"[?？]")
_INTERROGATIVE_RE = re.compile(
    r"(뭐|무엇|왜|어떻게|어떡|언제|어디|누가|누구|몇|얼마|어느|어떤|무슨|"
    r"궁금|알\s*수|해도\s*되|할\s*수|될\s*수|될지|되는지|"
    r"괜찮|맞나|아닌가|문제\s*없)"
)
_QUESTION_ENDING_RE = re.compile(
    r"(인가요|일까요|될까요|할까요|까요|나요|나여|나용|습니까|합니까|있나요|없나요|"
    r"맞나요|아닌가요|어때요|어떨까요|되나요|돼나요|가능한가요|가능할까요|"
    r"주시겠어요|주실\s*수|줄\s*수\s*있나요|부탁드려도\s*될까요)\s*$"
)
_REQUEST_CONFIRMATION_RE = re.compile(
    r"((확인|체크|검토|공유|정리|전달|컨펌|확정|결정).{0,12}"
    r"(해\s*주|해주세요|해\s*주세요|부탁|가능|필요|될지|되는지|주시|주실|알려))|"
    r"(알려\s*주|봐\s*주|보내\s*주|챙겨\s*주|부탁|주세요|주시|주실|해\s*주|해주)|"
    r"(알\s*수|될지|되는지)"
)

_FILLER_TEXTS = frozenset(
    {
        "음",
        "어",
        "네",
        "예",
        "아",
        "그",
        "그냥",
        "저기",
        "그러니까",
        "맞아요",
        "좋아요",
        "오케이",
        "okay",
        "ok",
    }
)

_TRAILING_TEXTS = frozenset(
    {
        "맞습니다",
        "맞아요",
        "좋습니다",
        "알겠습니다",
        "확인했습니다",
        "수고하셨습니다",
    }
)


@dataclass(frozen=True, slots=True)
class QuestionLaneFilterDecision:
    keep: bool
    reason: str | None = None


class QuestionLaneFilter:
    """LLM 호출 전, 질문 가능성이 전혀 없는 window만 제거한다."""

    def __init__(
        self,
        *,
        max_window_size: int = 3,
        min_window_compact_chars: int = 8,
    ) -> None:
        self._max_window_size = max(max_window_size, 1)
        self._min_window_compact_chars = max(min_window_compact_chars, 1)

    def decide(self, utterance: LiveQuestionUtterance) -> QuestionLaneFilterDecision:
        """빈 발화와 filler만 제거하고, 질문 판단은 window 단계로 미룬다."""

        text = _normalize_text(utterance.text)
        if not text:
            return QuestionLaneFilterDecision(False, "empty")

        compact = _compact_text(text)
        if not compact:
            return QuestionLaneFilterDecision(False, "empty")

        lower = compact.lower()
        if lower in _FILLER_TEXTS:
            return QuestionLaneFilterDecision(False, "filler_only")

        if lower in _TRAILING_TEXTS:
            return QuestionLaneFilterDecision(False, "tail_only")

        return QuestionLaneFilterDecision(True)

    def select_window(
        self,
        utterances: list[LiveQuestionUtterance],
    ) -> list[LiveQuestionUtterance]:
        """질문/확인 요청 후보가 있는 안정화 발화 window만 LLM으로 보낸다."""

        selected = list(utterances[-self._max_window_size :])
        if not selected:
            return []

        compact_length = sum(len(_compact_text(item.text)) for item in selected)
        if compact_length < self._min_window_compact_chars:
            return []

        if not any(_has_question_candidate_signal(item.text) for item in selected):
            return []

        return selected


def build_window_signature(
    utterances: list[LiveQuestionUtterance],
    open_question_ids: list[str],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """같은 window를 반복해서 LLM으로 보내지 않기 위한 안정적인 signature."""

    text_signature = tuple(_compact_text(item.text).lower() for item in utterances)
    return text_signature, tuple(open_question_ids)


def _normalize_text(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", (text or "").strip())


def _compact_text(text: str) -> str:
    cleaned = _PUNCTUATION_RE.sub("", text or "")
    return cleaned.replace(" ", "")


def _has_question_candidate_signal(text: str) -> bool:
    """STT가 의문부호/의문어미를 잃어도 확인 요청 후보는 살린다."""

    normalized = _normalize_text(text)
    compact = _compact_text(normalized)
    if not compact:
        return False
    if _QUESTION_MARK_RE.search(normalized):
        return True
    if _QUESTION_ENDING_RE.search(normalized):
        return True
    if _INTERROGATIVE_RE.search(normalized):
        return True
    return bool(_REQUEST_CONFIRMATION_RE.search(normalized))
