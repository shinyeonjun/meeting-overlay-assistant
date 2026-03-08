"""회의 이벤트 분석 규칙 정의."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from backend.app.domain.models.meeting_event import MeetingEvent
from backend.app.domain.models.utterance import Utterance
from backend.app.domain.shared.enums import EventPriority, EventState, EventType
from backend.app.services.analysis.rules.rule_config import AnalysisRuleConfig


@dataclass(frozen=True)
class EventRuleContext:
    """이벤트 규칙 평가에 필요한 입력."""

    utterance: Utterance
    text: str
    emitted_event_types: frozenset[EventType]


class EventRule(Protocol):
    """이벤트 생성 규칙 인터페이스."""

    def create_event(self, context: EventRuleContext) -> MeetingEvent | None:
        """규칙에 맞으면 이벤트를 만들고 아니면 None을 반환한다."""


@dataclass(frozen=True)
class QuestionRule:
    """질문 발화를 감지한다."""

    question_patterns: tuple[re.Pattern[str], ...]

    def create_event(self, context: EventRuleContext) -> MeetingEvent | None:
        if not (
            context.text.endswith("?")
            or any(pattern.search(context.text) for pattern in self.question_patterns)
        ):
            return None
        return MeetingEvent.create(
            session_id=context.utterance.session_id,
            event_type=EventType.QUESTION,
            title=context.text,
            body="질문이 감지되었습니다.",
            state=EventState.OPEN,
            priority=EventPriority.QUESTION,
            source_utterance_id=context.utterance.id,
            evidence_text=context.text,
            input_source=context.utterance.input_source,
        )


@dataclass(frozen=True)
class DecisionRule:
    """결정 발화를 감지한다."""

    keywords: tuple[str, ...]

    def create_event(self, context: EventRuleContext) -> MeetingEvent | None:
        if not any(keyword in context.text for keyword in self.keywords):
            return None
        return MeetingEvent.create(
            session_id=context.utterance.session_id,
            event_type=EventType.DECISION,
            title=context.text,
            body="결정 사항 후보가 감지되었습니다.",
            state=EventState.CONFIRMED,
            priority=EventPriority.DECISION,
            source_utterance_id=context.utterance.id,
            evidence_text=context.text,
            input_source=context.utterance.input_source,
        )


@dataclass(frozen=True)
class ActionItemRule:
    """액션 아이템 발화를 감지한다."""

    keywords: tuple[str, ...]
    due_date_patterns: tuple[re.Pattern[str], ...]
    assignee_patterns: tuple[re.Pattern[str], ...]

    def create_event(self, context: EventRuleContext) -> MeetingEvent | None:
        if not any(keyword in context.text for keyword in self.keywords):
            return None

        due_date = self._extract_first_match(self.due_date_patterns, context.text)
        assignee = self._extract_first_match(self.assignee_patterns, context.text)
        return MeetingEvent.create(
            session_id=context.utterance.session_id,
            event_type=EventType.ACTION_ITEM,
            title=context.text,
            body="액션 아이템이 감지되었습니다.",
            state=EventState.CONFIRMED if assignee or due_date else EventState.CANDIDATE,
            priority=EventPriority.ACTION_ITEM,
            source_utterance_id=context.utterance.id,
            assignee=assignee,
            due_date=due_date,
            evidence_text=context.text,
            input_source=context.utterance.input_source,
        )

    @staticmethod
    def _extract_first_match(patterns: tuple[re.Pattern[str], ...], text: str) -> str | None:
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                return match.group(1)
        return None


@dataclass(frozen=True)
class RiskRule:
    """리스크 발화를 감지한다."""

    keywords: tuple[str, ...]

    def create_event(self, context: EventRuleContext) -> MeetingEvent | None:
        if not any(keyword in context.text for keyword in self.keywords):
            return None
        return MeetingEvent.create(
            session_id=context.utterance.session_id,
            event_type=EventType.RISK,
            title=context.text,
            body="리스크 신호가 감지되었습니다.",
            state=EventState.OPEN,
            priority=EventPriority.RISK,
            source_utterance_id=context.utterance.id,
            evidence_text=context.text,
            input_source=context.utterance.input_source,
        )


@dataclass(frozen=True)
class TopicRule:
    """설명성 발화를 단발 topic 이벤트로 감지한다."""

    minimum_length: int
    minimum_token_count: int
    minimum_unique_token_count: int
    max_numeric_ratio: float
    blocked_patterns: tuple[re.Pattern[str], ...]
    title_max_length: int
    topic_group_max_length: int
    token_pattern: re.Pattern[str] = re.compile(r"[가-힣A-Za-z]{2,}")

    def create_event(self, context: EventRuleContext) -> MeetingEvent | None:
        if context.emitted_event_types:
            return None

        compact_text = re.sub(r"\s+", " ", context.text).strip()
        if len(compact_text) < self.minimum_length:
            return None
        if "?" in compact_text:
            return None
        if any(pattern.search(compact_text) for pattern in self.blocked_patterns):
            return None

        tokens = self.token_pattern.findall(compact_text)
        if len(tokens) < self.minimum_token_count:
            return None
        if len({token.lower() for token in tokens}) < self.minimum_unique_token_count:
            return None
        if self._numeric_ratio(compact_text) > self.max_numeric_ratio:
            return None

        return MeetingEvent.create(
            session_id=context.utterance.session_id,
            event_type=EventType.TOPIC,
            title=self._build_topic_title(compact_text),
            body="현재 주제 후보가 감지되었습니다.",
            state=EventState.ACTIVE,
            priority=EventPriority.TOPIC,
            source_utterance_id=context.utterance.id,
            topic_group=self._build_topic_group(compact_text),
            evidence_text=context.text,
            input_source=context.utterance.input_source,
        )

    def _build_topic_title(self, text: str) -> str:
        if len(text) <= self.title_max_length:
            return text
        return text[: self.title_max_length].rstrip() + "..."

    def _build_topic_group(self, text: str) -> str:
        normalized = re.sub(r"[^\w가-힣]+", "", text.lower()).strip()
        normalized = re.sub(r"\s+", "-", normalized)
        return f"topic-{normalized[: self.topic_group_max_length]}"

    @staticmethod
    def _numeric_ratio(text: str) -> float:
        compact_text = re.sub(r"\s+", "", text)
        if not compact_text:
            return 0.0
        digit_count = sum(1 for character in compact_text if character.isdigit())
        return digit_count / len(compact_text)


def create_default_event_rules(config: AnalysisRuleConfig) -> tuple[EventRule, ...]:
    """설정 기반 기본 분석 규칙 목록을 생성한다."""
    rules: list[EventRule] = [
        QuestionRule(
            question_patterns=tuple(
                re.compile(pattern, re.IGNORECASE) for pattern in config.question_patterns
            )
        ),
        DecisionRule(keywords=config.decision_keywords),
        ActionItemRule(
            keywords=config.action_keywords,
            due_date_patterns=tuple(re.compile(pattern) for pattern in config.due_date_patterns),
            assignee_patterns=tuple(re.compile(pattern) for pattern in config.assignee_patterns),
        ),
        RiskRule(keywords=config.risk_keywords),
    ]

    if config.enable_topic_events:
        rules.append(
            TopicRule(
                minimum_length=config.topic_minimum_length,
                minimum_token_count=config.topic_minimum_token_count,
                minimum_unique_token_count=config.topic_minimum_unique_token_count,
                max_numeric_ratio=config.topic_max_numeric_ratio,
                blocked_patterns=tuple(
                    re.compile(pattern, re.IGNORECASE) for pattern in config.topic_blocked_patterns
                ),
                title_max_length=config.topic_title_max_length,
                topic_group_max_length=config.topic_group_max_length,
            )
        )

    return tuple(rules)
