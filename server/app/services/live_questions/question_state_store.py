"""실시간 질문 보드 메모리 상태."""

from __future__ import annotations

from dataclasses import replace
from threading import Lock

from server.app.domain.events.meeting_event import MeetingEvent
from server.app.domain.shared.enums import EventState, EventType
from server.app.services.live_questions.models import (
    LiveQuestionItem,
    LiveQuestionOperation,
    LiveQuestionResult,
)


class LiveQuestionStateStore:
    """세션별 열린 질문 상태를 메모리에서 관리한다."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._open_questions_by_session: dict[str, list[MeetingEvent]] = {}

    def list_open_questions(self, session_id: str) -> list[LiveQuestionItem]:
        """세션의 열린 질문 요약을 반환한다."""

        with self._lock:
            questions = list(self._open_questions_by_session.get(session_id, ()))
        return [
            LiveQuestionItem(
                id=item.id,
                summary=item.title,
                speaker_label=item.speaker_label,
            )
            for item in questions
            if item.state == EventState.OPEN
        ]

    def apply_result(self, result: LiveQuestionResult) -> list[MeetingEvent]:
        """질문 분석 결과를 적용하고, 변경된 이벤트 목록을 반환한다."""

        with self._lock:
            current = list(self._open_questions_by_session.get(result.session_id, ()))
            changed: list[MeetingEvent] = []

            for operation in result.operations:
                applied = self._apply_operation(
                    session_id=result.session_id,
                    current=current,
                    operation=operation,
                )
                if applied is not None:
                    changed.append(applied)

            self._open_questions_by_session[result.session_id] = [
                item for item in current if item.state == EventState.OPEN
            ]
            return changed

    def clear_session(self, session_id: str) -> None:
        """세션 상태를 정리한다."""

        with self._lock:
            self._open_questions_by_session.pop(session_id, None)

    def _apply_operation(
        self,
        *,
        session_id: str,
        current: list[MeetingEvent],
        operation: LiveQuestionOperation,
    ) -> MeetingEvent | None:
        if operation.op == "add":
            summary = (operation.summary or "").strip()
            if not summary:
                return None
            normalized_summary = MeetingEvent.normalize_title(summary)
            for existing in current:
                if existing.state != EventState.OPEN:
                    continue
                if existing.normalized_title == normalized_summary:
                    return None

            event = MeetingEvent.create(
                session_id=session_id,
                event_type=EventType.QUESTION,
                title=summary,
                state=EventState.OPEN,
                source_utterance_id=(
                    operation.evidence_utterance_ids[0]
                    if operation.evidence_utterance_ids
                    else None
                ),
                speaker_label=operation.speaker_label,
                evidence_text=None,
            )
            current.insert(0, event)
            return event

        if operation.op == "close":
            target_id = operation.target_question_id
            if not target_id:
                return None
            for index, existing in enumerate(current):
                if existing.id != target_id:
                    continue
                if existing.state != EventState.OPEN:
                    return None
                closed = replace(
                    existing,
                    state=EventState.ANSWERED,
                    updated_at_ms=existing.updated_at_ms + 1,
                )
                current[index] = closed
                return closed

        return None
