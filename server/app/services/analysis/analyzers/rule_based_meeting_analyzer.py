"""규칙 기반 회의 분석기."""

from __future__ import annotations

from pathlib import Path

from server.app.domain.models.meeting_event import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.domain.shared.enums import EventType
from server.app.services.analysis.analyzers.analyzer import MeetingAnalyzer
from server.app.services.analysis.rules.event_rules import (
    EventRule,
    EventRuleContext,
    create_default_event_rules,
)
from server.app.services.analysis.rules.rule_config import load_analysis_rule_config


DEFAULT_ANALYSIS_RULES_PATH = (
    Path(__file__).resolve().parents[4] / "config" / "analysis_rules.json"
)


class RuleBasedMeetingAnalyzer(MeetingAnalyzer):
    """규칙 집합을 순회해 구조화 이벤트를 만드는 분석기."""

    def __init__(
        self,
        rules: tuple[EventRule, ...] | None = None,
        rules_config_path: str | Path | None = None,
    ) -> None:
        if rules is not None:
            self._rules = rules
            return

        config_path = Path(rules_config_path) if rules_config_path else DEFAULT_ANALYSIS_RULES_PATH
        config = load_analysis_rule_config(config_path)
        self._rules = create_default_event_rules(config)

    def analyze(self, utterance: Utterance) -> list[MeetingEvent]:
        """발화에서 이벤트를 추출한다."""
        text = utterance.text.strip()
        if not text:
            return []

        emitted_event_types: set[EventType] = set()
        events: list[MeetingEvent] = []

        for rule in self._rules:
            context = EventRuleContext(
                utterance=utterance,
                text=text,
                emitted_event_types=frozenset(emitted_event_types),
            )
            event = rule.create_event(context)
            if event is None:
                continue

            events.append(event)
            emitted_event_types.add(event.event_type)

        return events
