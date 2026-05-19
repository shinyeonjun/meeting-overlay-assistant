"""세션 후처리 중 canonical transcript/event 상태를 교체하고 복구한다."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from server.app.domain.events import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.repositories.contracts.events.event_repository import (
    MeetingEventRepository,
)
from server.app.repositories.contracts.utterance_repository import UtteranceRepository
from server.app.services.events.meeting_event_service import MeetingEventService
from server.app.services.reports.refinement import (
    TranscriptCorrectionDocument,
    TranscriptCorrectionStore,
)
from server.app.services.sessions.workspace_summary_models import (
    WorkspaceSummaryDocument,
)
from server.app.services.sessions.workspace_summary_store import WorkspaceSummaryStore


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CanonicalStateSnapshot:
    utterances: tuple[Utterance, ...]
    events: tuple[MeetingEvent, ...]
    correction_document: TranscriptCorrectionDocument | None
    workspace_summary_document: WorkspaceSummaryDocument | None


class CanonicalStateStore:
    """후처리 전후 canonical 상태 저장, 초기화, 복구를 담당한다."""

    def __init__(
        self,
        *,
        utterance_repository: UtteranceRepository | None,
        event_repository: MeetingEventRepository | None,
        event_service: MeetingEventService | None,
        transcript_correction_store: TranscriptCorrectionStore | None,
        workspace_summary_store: WorkspaceSummaryStore | None,
    ) -> None:
        self._utterance_repository = utterance_repository
        self._event_repository = event_repository
        self._event_service = event_service
        self._transcript_correction_store = transcript_correction_store
        self._workspace_summary_store = workspace_summary_store

    def snapshot(self, session_id: str) -> CanonicalStateSnapshot:
        utterance_repository = self._require_utterance_repository()
        event_repository = self._require_event_repository()
        return CanonicalStateSnapshot(
            utterances=tuple(utterance_repository.list_by_session(session_id)),
            events=tuple(event_repository.list_by_session(session_id)),
            correction_document=(
                self._transcript_correction_store.load(session_id=session_id)
                if self._transcript_correction_store is not None
                else None
            ),
            workspace_summary_document=(
                self._workspace_summary_store.load(session_id=session_id)
                if self._workspace_summary_store is not None
                else None
            ),
        )

    def replace(
        self,
        *,
        session_id: str,
        utterances: list[Utterance],
        events: list[MeetingEvent],
    ) -> None:
        utterance_repository = self._require_utterance_repository()
        event_repository = self._require_event_repository()
        event_service = self._require_event_service()

        self._clear_transcript_corrections(session_id)
        self._clear_workspace_summary(session_id)
        utterance_repository.delete_by_session(session_id)
        for utterance in utterances:
            utterance_repository.save(utterance)

        event_repository.delete_by_session(session_id)
        for event in events:
            event_service.save_or_merge(event)

    def prepare_provisional_transcript(self, *, session_id: str) -> None:
        utterance_repository = self._require_utterance_repository()
        event_repository = self._require_event_repository()

        self._clear_transcript_corrections(session_id)
        self._clear_workspace_summary(session_id)
        utterance_repository.delete_by_session(session_id)
        event_repository.delete_by_session(session_id)

    def restore(
        self,
        *,
        session_id: str,
        snapshot: CanonicalStateSnapshot,
    ) -> None:
        try:
            utterance_repository = self._require_utterance_repository()
            event_repository = self._require_event_repository()

            self._clear_transcript_corrections(session_id)
            utterance_repository.delete_by_session(session_id)
            for utterance in snapshot.utterances:
                utterance_repository.save(utterance)

            event_repository.delete_by_session(session_id)
            for event in snapshot.events:
                event_repository.save(event)

            if self._transcript_correction_store is not None:
                if snapshot.correction_document is None:
                    self._transcript_correction_store.delete(session_id)
                else:
                    self._transcript_correction_store.save(snapshot.correction_document)
            if self._workspace_summary_store is not None:
                if snapshot.workspace_summary_document is None:
                    self._workspace_summary_store.delete(session_id)
                else:
                    self._workspace_summary_store.save(snapshot.workspace_summary_document)
        except Exception:
            logger.exception(
                "canonical transcript/event 복구 실패: session_id=%s",
                session_id,
            )

    def _clear_transcript_corrections(self, session_id: str) -> None:
        if self._transcript_correction_store is None:
            return
        self._transcript_correction_store.delete(session_id)

    def _clear_workspace_summary(self, session_id: str) -> None:
        if self._workspace_summary_store is None:
            return
        self._workspace_summary_store.delete(session_id)

    def _require_utterance_repository(self) -> UtteranceRepository:
        if self._utterance_repository is None:
            raise RuntimeError("후처리용 utterance repository가 필요합니다.")
        return self._utterance_repository

    def _require_event_repository(self) -> MeetingEventRepository:
        if self._event_repository is None:
            raise RuntimeError("후처리용 event repository가 필요합니다.")
        return self._event_repository

    def _require_event_service(self) -> MeetingEventService:
        if self._event_service is None:
            raise RuntimeError("후처리용 event repository가 필요합니다.")
        return self._event_service
