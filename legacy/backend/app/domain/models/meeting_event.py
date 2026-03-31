"""회의 이벤트 엔티티."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from time import time
from uuid import uuid4

from backend.app.domain.shared.enums import EventPriority, EventState, EventType


def _now_ms() -> int:
    return int(time() * 1000)


@dataclass(frozen=True)
class MeetingEvent:
    """회의 중 구조화된 단일 이벤트."""

    id: str
    session_id: str
    event_type: EventType
    title: str
    body: str | None
    state: EventState
    priority: EventPriority
    topic_group: str | None
    source_utterance_id: str | None
    speaker_label: str | None = None
    assignee: str | None = None
    due_date: str | None = None
    evidence_text: str | None = None
    source_screen_id: str | None = None
    created_at_ms: int = 0
    updated_at_ms: int = 0
    input_source: str | None = None
    insight_scope: str = "live"

    @classmethod
    def create(
        cls,
        session_id: str,
        event_type: EventType,
        title: str,
        state: EventState | str,
        priority: EventPriority | int,
        source_utterance_id: str | None,
        body: str | None = None,
        topic_group: str | None = None,
        speaker_label: str | None = None,
        assignee: str | None = None,
        due_date: str | None = None,
        evidence_text: str | None = None,
        source_screen_id: str | None = None,
        input_source: str | None = None,
        insight_scope: str = "live",
    ) -> "MeetingEvent":
        """새 이벤트를 생성한다."""
        now = _now_ms()
        return cls(
            id=f"evt-{uuid4().hex}",
            session_id=session_id,
            event_type=event_type,
            title=title,
            body=body,
            state=EventState(state),
            priority=EventPriority(priority),
            topic_group=topic_group,
            source_utterance_id=source_utterance_id,
            speaker_label=speaker_label,
            assignee=assignee,
            due_date=due_date,
            evidence_text=evidence_text,
            source_screen_id=source_screen_id,
            created_at_ms=now,
            updated_at_ms=now,
            input_source=input_source,
            insight_scope=insight_scope,
        )

    @property
    def normalized_title(self) -> str:
        """중복 비교용 정규화 제목을 반환한다."""
        return self.normalize_title(self.title)

    @staticmethod
    def normalize_title(title: str) -> str:
        """저장과 병합 조회에 공통으로 쓰는 제목 정규화 규칙."""
        compact_text = re.sub(r"\s+", " ", title.strip().lower())
        return re.sub(r"[^\w가-힣]+", "", compact_text)

    def can_merge_with(self, candidate: "MeetingEvent") -> bool:
        """기존 이벤트와 후보 이벤트를 병합할 수 있는지 판단한다."""
        if self.event_type != candidate.event_type:
            return False
        if self.state == EventState.CLOSED:
            return False
        if self.event_type == EventType.TOPIC:
            return False
        if self.event_type not in {
            EventType.QUESTION,
            EventType.DECISION,
            EventType.ACTION_ITEM,
            EventType.RISK,
        }:
            return False
        return self.normalized_title == candidate.normalized_title

    def merge_with(self, candidate: "MeetingEvent") -> "MeetingEvent":
        """후보 이벤트를 반영해 기존 이벤트를 갱신한다."""
        if self.event_type == EventType.TOPIC:
            return replace(
                self,
                title=candidate.title,
                body=candidate.body,
                topic_group=candidate.topic_group,
                source_utterance_id=candidate.source_utterance_id or self.source_utterance_id,
                speaker_label=candidate.speaker_label or self.speaker_label,
                evidence_text=candidate.evidence_text or self.evidence_text,
                updated_at_ms=candidate.updated_at_ms,
            )
        return replace(
            self,
            body=self.body or candidate.body,
            state=self._merge_state(candidate),
            priority=max(self.priority, candidate.priority),
            speaker_label=self.speaker_label or candidate.speaker_label,
            assignee=self.assignee or candidate.assignee,
            due_date=self.due_date or candidate.due_date,
            source_utterance_id=candidate.source_utterance_id or self.source_utterance_id,
            evidence_text=self.evidence_text or candidate.evidence_text,
            updated_at_ms=candidate.updated_at_ms,
        )

    def _merge_state(self, candidate: "MeetingEvent") -> EventState:
        """기존 상태와 후보 상태를 비교해 더 적절한 상태를 반환한다."""
        if self.state == candidate.state:
            return self.state
        if self.state == EventState.CANDIDATE and candidate.state == EventState.CONFIRMED:
            return EventState.CONFIRMED
        return self.state
