"""실시간 이벤트를 비동기로 보정하는 서비스."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from server.app.core.persistence_types import TransactionManager
from server.app.core.persistence_types import TransactionManager
from server.app.domain.models.utterance import Utterance
from server.app.domain.shared.enums import EventType
from server.app.services.analysis.analyzers.analyzer import MeetingAnalyzer
from server.app.services.events.meeting_event_service import MeetingEventService


logger = logging.getLogger(__name__)


class NoOpLiveEventCorrectionService:
    """아무 것도 하지 않는 보정 서비스."""

    def submit(self, utterance: Utterance) -> None:
        return None


class AsyncLiveEventCorrectionService:
    """발화 저장 후 LLM 기반 보정을 백그라운드에서 수행한다."""

    def __init__(
        self,
        analyzer: MeetingAnalyzer,
        event_service: MeetingEventService,
        transaction_manager: TransactionManager,
        target_event_types: tuple[EventType, ...],
        min_utterance_confidence: float,
        min_text_length: int,
        max_workers: int,
    ) -> None:
        self._analyzer = analyzer
        self._event_service = event_service
        self._transaction_manager = transaction_manager
        self._target_event_types = target_event_types
        self._min_utterance_confidence = min_utterance_confidence
        self._min_text_length = min_text_length
        self._executor = ThreadPoolExecutor(
            max_workers=max(max_workers, 1),
            thread_name_prefix="live-event-corrector",
        )

    def submit(self, utterance: Utterance) -> None:
        """보정 대상이면 백그라운드 작업으로 제출한다."""
        if not self._should_submit(utterance):
            return

        self._executor.submit(self.correct, utterance)

    def correct(self, utterance: Utterance) -> list:
        """발화를 다시 분석하고 기존 이벤트를 보정한다."""
        try:
            corrected_events = [
                event
                for event in self._analyzer.analyze(utterance)
                if event.event_type in self._target_event_types
            ]
            with self._transaction_manager.transaction() as connection:
                persisted_events = self._event_service.apply_source_utterance_corrections(
                    session_id=utterance.session_id,
                    source_utterance_id=utterance.id,
                    corrected_events=corrected_events,
                    target_event_types=self._target_event_types,
                    connection=connection,
                )
            logger.debug(
                "실시간 이벤트 보정 완료: session_id=%s utterance_id=%s corrected_events=%d",
                utterance.session_id,
                utterance.id,
                len(persisted_events),
            )
            return persisted_events
        except Exception:
            logger.exception(
                "실시간 이벤트 보정 실패: session_id=%s utterance_id=%s",
                utterance.session_id,
                utterance.id,
            )
            return []

    def _should_submit(self, utterance: Utterance) -> bool:
        if utterance.confidence < self._min_utterance_confidence:
            return False
        compact_text = utterance.text.strip()
        return len(compact_text) >= self._min_text_length
