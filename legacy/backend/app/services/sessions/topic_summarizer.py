"""현재 주제 요약기."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from threading import Lock
from typing import Protocol

from backend.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)


class TopicSummarizer(Protocol):
    """현재 주제 요약기 인터페이스."""

    def summarize(
        self,
        session_id: str,
        topic_texts: list[str],
        fallback_topic: str | None = None,
    ) -> str | None:
        """최근 발화 묶음을 기반으로 현재 주제를 요약한다."""


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
        "과",
        "로",
    )
    _STOPWORDS = frozenset(
        {
            "그냥",
            "일단",
            "이거",
            "이런",
            "저건",
            "약간",
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
    """LLM 없이 휴리스틱 요약값을 반환한다."""

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


@dataclass
class _TopicSummaryCacheEntry:
    signature: str
    summary: str | None


class LLMTopicSummarizer:
    """최근 발화 묶음을 Ollama/LLM으로 짧은 주제로 요약한다."""

    _MAX_TOPIC_LENGTH = 36

    def __init__(self, completion_client: LLMCompletionClient) -> None:
        self._completion_client = completion_client
        self._cache: dict[str, _TopicSummaryCacheEntry] = {}
        self._lock = Lock()
        self._fallback_summarizer = TopicHeuristicSummarizer()

    def summarize(
        self,
        session_id: str,
        topic_texts: list[str],
        fallback_topic: str | None = None,
    ) -> str | None:
        normalized_texts = [text.strip() for text in topic_texts if text and text.strip()]
        if not normalized_texts:
            return fallback_topic

        signature = "\n".join(normalized_texts[-5:])
        with self._lock:
            cached = self._cache.get(session_id)
            if cached is not None and cached.signature == signature:
                return cached.summary or fallback_topic

        prompt = self._build_prompt(normalized_texts, fallback_topic)
        try:
            raw_summary = self._completion_client.complete(prompt)
        except Exception:
            raw_summary = ""

        heuristic_fallback = self._fallback_summarizer.summarize(
            session_id=session_id,
            topic_texts=normalized_texts,
            fallback_topic=fallback_topic,
        )
        summary = self._normalize_summary(raw_summary, heuristic_fallback)
        with self._lock:
            self._cache[session_id] = _TopicSummaryCacheEntry(
                signature=signature,
                summary=summary,
            )
        return summary or heuristic_fallback

    def _build_prompt(self, topic_texts: list[str], fallback_topic: str | None) -> str:
        joined_topic_lines = "\n".join(f"- {text}" for text in topic_texts[-5:])
        fallback_line = fallback_topic or "없음"
        return (
            "당신은 회의 HUD의 현재 주제 요약기다.\n"
            "아래 최근 발화들을 보고 지금 논의 중인 주제를 아주 짧은 한국어 명사구로 요약하라.\n"
            "규칙:\n"
            "- 18자 이내를 목표로 한다.\n"
            "- 문장형 말투를 쓰지 않는다.\n"
            "- 마지막 발화를 그대로 복사하지 않는다.\n"
            "- 자막처럼 길게 쓰지 않는다.\n"
            "- 여러 발화에서 반복되는 공통 개념만 남긴다.\n"
            "- 출력은 요약 한 줄만 반환한다.\n"
            f"- fallback 주제: {fallback_line}\n"
            "\n"
            "[최근 발화]\n"
            f"{joined_topic_lines}\n"
        )

    def _normalize_summary(self, raw_summary: str, fallback_topic: str | None) -> str | None:
        summary = raw_summary.strip()
        if not summary:
            return fallback_topic

        summary = summary.splitlines()[0].strip()
        summary = summary.strip("`\"' ")
        summary = re.sub(r"^(현재 주제|주제)\s*[:：]\s*", "", summary)
        summary = re.sub(r"\s+", " ", summary)
        if len(summary) > self._MAX_TOPIC_LENGTH:
            summary = summary[: self._MAX_TOPIC_LENGTH].rstrip() + "..."
        return summary or fallback_topic
