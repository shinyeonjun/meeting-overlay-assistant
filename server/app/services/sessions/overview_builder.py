"""세션 overview 조립기."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from server.app.domain.models.meeting_event import MeetingEvent
from server.app.domain.session import MeetingSession
from server.app.domain.shared.enums import EventState, EventType
from server.app.services.sessions.workspace_summary_models import WorkspaceSummaryDocument


@dataclass(frozen=True)
class OverviewEventItem:
    """overview에 노출할 단일 이벤트 항목."""

    id: str
    title: str
    state: EventState
    speaker_label: str | None


@dataclass(frozen=True)
class SessionOverview:
    """세션 overview 응답용 도메인 모델."""

    session: MeetingSession
    current_topic: str | None
    questions: list[OverviewEventItem]
    decisions: list[OverviewEventItem]
    action_items: list[OverviewEventItem]
    risks: list[OverviewEventItem]
    workspace_summary: WorkspaceSummaryDocument | None = None
    recent_average_latency_ms: float | None = None
    recent_utterance_count_by_source: dict[str, int] | None = None
    insight_metrics: dict[str, int] | None = None


class SessionOverviewBuilder:
    """세션과 이벤트 목록으로 live overview를 조립한다."""

    _TOPIC_TOKEN_PATTERN = re.compile(r"[가-힣A-Za-z0-9]{2,}")
    _TOPIC_PARTICLE_SUFFIXES = (
        "으로",
        "에서",
        "이다",
        "하고",
        "에게",
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
        "도",
        "만",
        "와",
        "과",
        "로",
    )
    _TOPIC_STOPWORDS = frozenset(
        {
            "그냥",
            "일단",
            "이거",
            "이런",
            "저런",
            "약간",
            "뭔가",
            "진짜",
            "지금",
            "여기",
            "그거",
            "저거",
            "하는",
            "같은",
            "되고",
            "나오고",
            "맞아요",
            "느낌은",
            "잡아지긴",
        }
    )

    def build(self, session: MeetingSession, events: list[MeetingEvent]) -> SessionOverview:
        """overview 응답용 도메인 모델을 생성한다."""
        return SessionOverview(
            session=session,
            current_topic=self._resolve_current_topic(events),
            questions=self._filter_events(events, EventType.QUESTION),
            decisions=self._filter_events(events, EventType.DECISION),
            action_items=self._filter_events(events, EventType.ACTION_ITEM),
            risks=self._filter_events(events, EventType.RISK),
        )

    def _resolve_current_topic(self, events: list[MeetingEvent]) -> str | None:
        topic_events = [event for event in events if event.event_type == EventType.TOPIC]
        if not topic_events:
            return None
        if len(topic_events) == 1:
            return topic_events[-1].title

        recent_topic_events = topic_events[-5:]
        topic_summary = self._build_topic_summary(recent_topic_events)
        if topic_summary is not None:
            return topic_summary
        return topic_events[-1].title

    def _build_topic_summary(self, topic_events: list[MeetingEvent]) -> str | None:
        token_counter: Counter[str] = Counter()
        ordered_tokens: list[str] = []

        for event in topic_events:
            seen_in_event: set[str] = set()
            for token in self._extract_topic_tokens(event.title):
                if token in seen_in_event:
                    continue
                seen_in_event.add(token)
                token_counter[token] += 1
                ordered_tokens.append(token)

        stable_tokens = [
            token
            for token in ordered_tokens
            if token_counter[token] >= 2
        ]
        deduplicated_tokens = list(dict.fromkeys(stable_tokens))
        if not deduplicated_tokens:
            return None

        return " / ".join(deduplicated_tokens[:3]) + " 논의"

    def _extract_topic_tokens(self, text: str) -> list[str]:
        tokens: list[str] = []
        for token in self._TOPIC_TOKEN_PATTERN.findall(text.lower()):
            token = self._normalize_topic_token(token)
            if token in self._TOPIC_STOPWORDS:
                continue
            tokens.append(token)
        return tokens

    def _normalize_topic_token(self, token: str) -> str:
        for suffix in self._TOPIC_PARTICLE_SUFFIXES:
            if len(token) > len(suffix) + 1 and token.endswith(suffix):
                return token[: -len(suffix)]
        return token

    def _filter_events(
        self,
        events: list[MeetingEvent],
        event_type: EventType,
    ) -> list[OverviewEventItem]:
        return [
            OverviewEventItem(
                id=event.id,
                title=event.title,
                state=event.state,
                speaker_label=event.speaker_label,
            )
            for event in events
            if event.event_type == event_type
        ]
