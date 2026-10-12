"""session 후처리 결과가 교체하는 canonical transcript/event 상태를 관리한다."""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass

from server.app.contexts.insight import MeetingEvent, MeetingEventService
from server.app.contexts.reporting import TranscriptCorrectionDocument, TranscriptCorrectionStore
from server.app.domain.models.utterance import (
    POST_PROCESSING_DRAFT_SOURCE,
    Utterance,
    select_visible_utterances,
)
from server.app.repositories.contracts.events.event_repository import (
    MeetingEventRepository,
)
from server.app.repositories.contracts.utterance_repository import UtteranceRepository


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CanonicalStateSnapshot:
    """복구에 쓰는 canonical 상태의 저장 시점 스냅샷이다."""

    utterances: tuple[Utterance, ...]
    events: tuple[MeetingEvent, ...]
    correction_document: TranscriptCorrectionDocument | None


class CanonicalTranscriptState:
    """세션의 canonical transcript/event를 스냅샷, 교체, 복구한다."""

    def __init__(
        self,
        *,
        utterance_repository: UtteranceRepository | None,
        event_repository: MeetingEventRepository | None,
        event_service: MeetingEventService | None,
        transcript_correction_store: TranscriptCorrectionStore | None,
        database=None,
    ) -> None:
        self._utterance_repository = utterance_repository
        self._event_repository = event_repository
        self._event_service = event_service
        self._transcript_correction_store = transcript_correction_store
        # canonical transcript 교체를 한 트랜잭션으로 묶을 때 쓴다 (PostgreSQLDatabase).
        self._database = database

    def snapshot(self, session_id: str) -> CanonicalStateSnapshot:
        """현재 canonical 상태를 복구용으로 스냅샷한다."""

        return CanonicalStateSnapshot(
            utterances=tuple(select_visible_utterances(self._utterance_repository.list_by_session(session_id))),
            events=tuple(self._event_repository.list_by_session(session_id)),
            correction_document=(
                self._transcript_correction_store.load(session_id=session_id)
                if self._transcript_correction_store is not None
                else None
            ),
        )

    @contextmanager
    def _transaction(self) -> Generator[object | None]:
        """database가 있으면 트랜잭션 connection을, 없으면 None(개별 commit)을 준다."""

        if self._database is None:
            yield None
            return
        with self._database.transaction() as connection:
            yield connection

    def replace(
        self,
        *,
        session_id: str,
        utterances: list[Utterance],
        events: list[MeetingEvent],
    ) -> None:
        """canonical transcript/event를 후처리 결과로 교체한다."""

        # 원본 삭제와 canonical 저장이 중간에 끊기면 transcript가 비므로 한 트랜잭션으로 묶는다.
        with self._transaction() as connection:
            self._utterance_repository.delete_by_session(session_id, connection=connection)
            self._utterance_repository.save_many(utterances, connection=connection)

            self._event_repository.delete_by_session(session_id, connection=connection)
            for event in events:
                self._event_service.save_or_merge(event, connection=connection)
        self._clear_transcript_corrections(session_id)

    def discard_provisional(self, session_id: str) -> None:
        """진행 중 초안(provisional) transcript를 지운다."""

        self._utterance_repository.delete_by_session(
            session_id,
            transcript_source=POST_PROCESSING_DRAFT_SOURCE,
        )

    def restore(
        self,
        *,
        session_id: str,
        snapshot: CanonicalStateSnapshot,
    ) -> None:
        """스냅샷 시점의 canonical 상태로 되돌린다."""

        # 복구는 스냅샷을 그대로 되돌린다. 교체 경로처럼 save_or_merge로 병합하면 저장 당시 상태와 달라진다.
        try:
            with self._transaction() as connection:
                self._utterance_repository.delete_by_session(session_id, connection=connection)
                self._utterance_repository.save_many(snapshot.utterances, connection=connection)

                self._event_repository.delete_by_session(session_id, connection=connection)
                for event in snapshot.events:
                    self._event_repository.save(event, connection=connection)

            if self._transcript_correction_store is not None:
                if snapshot.correction_document is None:
                    self._transcript_correction_store.delete(session_id)
                else:
                    self._transcript_correction_store.save(snapshot.correction_document)
        except Exception:
            logger.exception(
                "canonical transcript/event 복구 실패: session_id=%s",
                session_id,
            )

    def _clear_transcript_corrections(self, session_id: str) -> None:
        if self._transcript_correction_store is None:
            return
        self._transcript_correction_store.delete(session_id)
