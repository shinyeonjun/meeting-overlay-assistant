"""세션 영역의 heuristic 서비스를 제공한다."""
from __future__ import annotations

import re
from collections import Counter


class TopicHeuristicSummarizer:
    """LLM 없이 최근 발화 묶음에서 현재 주제를 추정한다."""

    _MAX_TOPIC_LENGTH = 36
    _TOKEN_PATTERN = re.compile(r"[가-힣A-Za-z0-9]{2,}")
    _PARTICLE_SUFFIXES = (
        "으로",
        "에서",
        "이다",
        "하고",
        "하게",
        "에는",
        "에서",
        "으로",
        "은",
        "는",
        "이",
        "가",
        "을",
        "를",
        "에",
        "의",
        "만",
        "도",
        "고",
        "로",
    )
    _STOPWORDS = frozenset(
        {
            "그냥",
            "일단",
            "이거",
            "이런",
            "저거",
            "조금",
            "뭔가",
            "진짜",
            "지금",
            "여기",
            "저기",
            "하는",
            "같은",
            "하고",
            "맞아요",
            "맞아",
            "일단은",
        }
    )

    def summarize(
        self,
        session_id: str,
        topic_texts: list[str],
        fallback_topic: str | None = None,
    ) -> str | None:
        del session_id
        normalized_texts = [text.strip() for text in topic_texts if text and text.strip()]
        if not normalized_texts:
            return fallback_topic

        summary = self._build_summary(normalized_texts)
        return summary or fallback_topic

    def _build_summary(self, topic_texts: list[str]) -> str | None:
        token_counter: Counter[str] = Counter()
        ordered_tokens: list[str] = []

        for text in topic_texts[-5:]:
            seen_in_text: set[str] = set()
            for token in self._extract_tokens(text):
                if token in seen_in_text:
                    continue
                seen_in_text.add(token)
                token_counter[token] += 1
                ordered_tokens.append(token)

        stable_tokens = [token for token in ordered_tokens if token_counter[token] >= 2]
        deduplicated_tokens = list(dict.fromkeys(stable_tokens))
        if not deduplicated_tokens:
            deduplicated_tokens = list(dict.fromkeys(ordered_tokens))
        if not deduplicated_tokens:
            return None

        if len(deduplicated_tokens) == 1:
            summary = f"{deduplicated_tokens[0]} 논의"
        else:
            summary = " / ".join(deduplicated_tokens[:2]) + " 논의"

        if len(summary) > self._MAX_TOPIC_LENGTH:
            return summary[: self._MAX_TOPIC_LENGTH].rstrip() + "..."
        return summary

    def _extract_tokens(self, text: str) -> list[str]:
        tokens: list[str] = []
        for token in self._TOKEN_PATTERN.findall(text.lower()):
            token = self._normalize_token(token)
            if token in self._STOPWORDS:
                continue
            tokens.append(token)
        return tokens

    def _normalize_token(self, token: str) -> str:
        for suffix in self._PARTICLE_SUFFIXES:
            if len(token) > len(suffix) + 1 and token.endswith(suffix):
                return token[: -len(suffix)]
        return token


class NoOpTopicSummarizer:
    """LLM 없이 heuristic 요약값을 반환한다."""

    def __init__(self) -> None:
        self._heuristic_summarizer = TopicHeuristicSummarizer()

    def summarize(
        self,
        session_id: str,
        topic_texts: list[str],
        fallback_topic: str | None = None,
    ) -> str | None:
        return self._heuristic_summarizer.summarize(
            session_id=session_id,
            topic_texts=topic_texts,
            fallback_topic=fallback_topic,
        )
