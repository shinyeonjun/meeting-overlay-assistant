"""회의 이벤트 엔티티."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from time import time
from uuid import uuid4

from server.app.domain.shared.enums import EventPriority, EventState, EventType


def _now_ms() -> int:
    return int(time() * 1000)


@dataclass(frozen=True)
class MeetingEvent:
    """회의 중 추출된 단일 인사이트 이벤트."""

    id: str
    session_id: str
    event_type: EventType
    title: str
    state: EventState
    source_utterance_id: str | None
    evidence_text: str | None = None
    speaker_label: str | None = None
    body: str | None = None
    created_at_ms: int = 0
    updated_at_ms: int = 0
    input_source: str | None = None
    insight_scope: str = "live"
    event_source: str = "live"
    processing_job_id: str | None = None
    finalized_at_ms: int | None = None

    @classmethod
    def create(
        cls,
        session_id: str,
        event_type: EventType,
        title: str,
        state: EventState | str,
        source_utterance_id: str | None,
        evidence_text: str | None = None,
        speaker_label: str | None = None,
        body: str | None = None,
        input_source: str | None = None,
        insight_scope: str = "live",
        event_source: str = "live",
        processing_job_id: str | None = None,
        finalized_at_ms: int | None = None,
        priority: int | EventPriority | None = None,
        assignee: str | None = None,
        due_date: str | None = None,
        topic_group: str | None = None,
    ) -> "MeetingEvent":
        """이벤트를 생성한다."""
        del priority, assignee, due_date, topic_group

        now = _now_ms()
        return cls(
            id=f"evt-{uuid4().hex}",
            session_id=session_id,
            event_type=event_type,
            title=title,
            state=EventState(state),
            source_utterance_id=source_utterance_id,
            evidence_text=evidence_text,
            speaker_label=speaker_label,
            body=body,
            created_at_ms=now,
            updated_at_ms=now,
            input_source=input_source,
            insight_scope=insight_scope,
            event_source=event_source,
            processing_job_id=processing_job_id,
            finalized_at_ms=finalized_at_ms,
        )

    @property
    def priority(self) -> EventPriority:
        """이전 코드 경로와 테스트를 위한 호환 우선순위."""

        default_priority_by_type = {
            EventType.TOPIC: EventPriority.TOPIC,
            EventType.QUESTION: EventPriority.QUESTION,
            EventType.DECISION: EventPriority.DECISION,
            EventType.ACTION_ITEM: EventPriority.ACTION_ITEM,
            EventType.RISK: EventPriority.RISK,
        }
        return default_priority_by_type.get(self.event_type, EventPriority.NONE)

    @property
    def assignee(self) -> str | None:
        """이전 이벤트 모델과의 호환용 필드."""

        return None

    @property
    def due_date(self) -> str | None:
        """이전 이벤트 모델과의 호환용 필드."""

        return None

    @property
    def topic_group(self) -> str | None:
        """이전 이벤트 모델과의 호환용 필드."""

        return None

    @property
    def normalized_title(self) -> str:
        """중복 비교용 정규화 제목을 반환한다."""

        return self.normalize_title(self.title)

    @staticmethod
    def normalize_title(title: str) -> str:
        """중복 병합 조회에 쓰는 공통 제목 정규화 규칙."""

        compact_text = re.sub(r"\s+", " ", title.strip().lower())
        return re.sub(r"[^\w가-힣]+", "", compact_text)

    def can_merge_with(self, candidate: "MeetingEvent") -> bool:
        """동일 이벤트로 병합 가능한지 반환한다."""

        if self.event_type != candidate.event_type:
            return False
        if self.state == EventState.CLOSED:
            return False
        if self.event_type == EventType.TOPIC:
            return False
        return self.normalized_title == candidate.normalized_title

    def merge_with(self, candidate: "MeetingEvent") -> "MeetingEvent":
        """후보 이벤트를 반영해 현재 이벤트를 갱신한다."""

        if self.event_type == EventType.TOPIC:
            return replace(
                self,
                title=candidate.title,
                body=candidate.body,
                source_utterance_id=candidate.source_utterance_id or self.source_utterance_id,
                speaker_label=candidate.speaker_label or self.speaker_label,
                evidence_text=candidate.evidence_text or self.evidence_text,
                input_source=candidate.input_source or self.input_source,
                updated_at_ms=candidate.updated_at_ms,
            )

        return replace(
            self,
            body=self.body or candidate.body,
            state=self._merge_state(candidate),
            source_utterance_id=candidate.source_utterance_id or self.source_utterance_id,
            evidence_text=self.evidence_text or candidate.evidence_text,
            speaker_label=self.speaker_label or candidate.speaker_label,
            input_source=self.input_source or candidate.input_source,
            updated_at_ms=candidate.updated_at_ms,
        )

    def _merge_state(self, candidate: "MeetingEvent") -> EventState:
        """기존 상태와 후보 상태를 비교해 유지할 상태를 반환한다."""

        if self.state == candidate.state:
            return self.state
        if self.event_type == EventType.DECISION and self.state == EventState.CONFIRMED:
            return candidate.state if candidate.state == EventState.UPDATED else self.state
        if self.event_type == EventType.RISK and self.state == EventState.OPEN:
            return candidate.state if candidate.state == EventState.RESOLVED else self.state
        if self.event_type == EventType.QUESTION and self.state == EventState.OPEN:
            return candidate.state if candidate.state == EventState.ANSWERED else self.state
        if self.event_type == EventType.ACTION_ITEM and self.state == EventState.OPEN:
            return candidate.state if candidate.state == EventState.CLOSED else self.state
        return self.state
