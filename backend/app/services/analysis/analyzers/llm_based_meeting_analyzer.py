"""LLM 기반 회의 분석기 뼈대."""

from __future__ import annotations

from backend.app.domain.models.meeting_event import MeetingEvent
from backend.app.domain.models.utterance import Utterance
from backend.app.domain.shared.enums import EventPriority, EventState, EventType
from backend.app.services.analysis.analyzers.analyzer import MeetingAnalyzer
from backend.app.services.analysis.event_type_policy import (
    INSIGHT_EVENT_TYPE_VALUES,
    normalize_event_type_token,
)
from backend.app.services.analysis.llm.contracts.llm_models import LLMAnalysisInput
from backend.app.services.analysis.llm.contracts.llm_provider import LLMAnalysisProvider
from backend.app.services.analysis.llm.providers.prompt_based_llm_analysis_provider import (
    PromptBasedLLMAnalysisProvider,
)


class LLMBasedMeetingAnalyzer(MeetingAnalyzer):
    """LLM provider 결과를 MeetingEvent로 변환하는 분석기."""

    def __init__(self, provider: LLMAnalysisProvider | None = None) -> None:
        self._provider = provider or PromptBasedLLMAnalysisProvider()

    def analyze(self, utterance: Utterance) -> list[MeetingEvent]:
        """LLM provider 결과를 도메인 이벤트로 변환한다."""
        text = utterance.text.strip()
        if not text:
            return []

        result = self._provider.analyze(
            LLMAnalysisInput(
                session_id=utterance.session_id,
                utterance_id=utterance.id,
                text=text,
            )
        )

        events: list[MeetingEvent] = []
        for candidate in result.candidates:
            candidate_event_type = normalize_event_type_token(candidate.event_type)
            if candidate_event_type not in INSIGHT_EVENT_TYPE_VALUES:
                continue
            try:
                event_type = EventType(candidate_event_type)
                event_state = EventState(candidate.state)
                event_priority = EventPriority(candidate.priority)
            except ValueError:
                continue

            events.append(
                MeetingEvent.create(
                    session_id=utterance.session_id,
                    event_type=event_type,
                    title=candidate.title,
                    body=candidate.body,
                    state=event_state,
                    priority=event_priority,
                    source_utterance_id=utterance.id,
                    assignee=candidate.assignee,
                    due_date=candidate.due_date,
                    topic_group=candidate.topic_group,
                    evidence_text=utterance.text,
                    input_source=utterance.input_source,
                )
            )

        return events
