"""세션 영역의 llm 서비스를 제공한다."""
from __future__ import annotations

import re
from dataclasses import dataclass
from threading import Lock

from server.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)
from server.app.services.sessions.topic_helpers.heuristic import TopicHeuristicSummarizer


@dataclass
class _TopicSummaryCacheEntry:
    signature: str
    summary: str | None


class LLMTopicSummarizer:
    """최근 발화 묶음을 LLM으로 현재 주제로 요약한다."""

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
            "당신은 회의 HUD용 현재 주제 요약기다.\n"
            "아래 최근 발화들을 보고 지금 논의 중인 주제를 아주 짧은 명사구로 요약하라.\n"
            "규칙:\n"
            "- 18자 이내를 목표로 한다.\n"
            "- 문장은 말투를 쓰지 않는다.\n"
            "- 마지막 발화를 그대로 복사하지 않는다.\n"
            "- 자막처럼 길게 쓰지 않는다.\n"
            "- 여러 발화에서 반복되는 공통 개념만 추린다.\n"
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
        summary = re.sub(r"^(현재 주제|주제)\s*[:：]?\s*", "", summary)
        summary = re.sub(r"\s+", " ", summary)
        if len(summary) > self._MAX_TOPIC_LENGTH:
            summary = summary[: self._MAX_TOPIC_LENGTH].rstrip() + "..."
        return summary or fallback_topic
