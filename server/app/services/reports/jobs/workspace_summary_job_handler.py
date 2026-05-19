"""노트 보정 후 workspace summary 생성과 저장을 처리한다."""

from __future__ import annotations

import logging

from server.app.repositories.contracts.events.event_repository import (
    MeetingEventRepository,
)
from server.app.repositories.contracts.session import SessionRepository
from server.app.repositories.contracts.session_post_processing_job_repository import (
    SessionPostProcessingJobRepository,
)
from server.app.services.reports.jobs.workspace_summary_execution import (
    WorkspaceSummaryExecutionCoordinator,
)
from server.app.services.reports.refinement import TranscriptCorrectionDocument
from server.app.services.sessions.workspace_summary_store import WorkspaceSummaryStore


logger = logging.getLogger(__name__)


class WorkspaceSummaryJobHandler:
    """노트 보정 결과를 기반으로 workspace summary artifact와 RAG 인덱스를 갱신한다."""

    def __init__(
        self,
        *,
        session_repository: SessionRepository,
        event_repository: MeetingEventRepository | None = None,
        workspace_summary_synthesizer=None,
        workspace_summary_store: WorkspaceSummaryStore | None = None,
        workspace_summary_knowledge_indexing_service=None,
        session_post_processing_job_repository: (
            SessionPostProcessingJobRepository | None
        ) = None,
        gpu_heavy_execution_gate=None,
        wait_timeout_seconds: float = 300.0,
        poll_interval_seconds: float = 5.0,
        gpu_heavy_poll_interval_seconds: float = 1.0,
    ) -> None:
        self._event_repository = event_repository
        self._workspace_summary_synthesizer = (
            None if callable(workspace_summary_synthesizer) else workspace_summary_synthesizer
        )
        self._workspace_summary_synthesizer_factory = (
            workspace_summary_synthesizer
            if callable(workspace_summary_synthesizer)
            else None
        )
        self._workspace_summary_store = workspace_summary_store
        self._workspace_summary_knowledge_indexing_service = (
            workspace_summary_knowledge_indexing_service
        )
        self._execution_coordinator = WorkspaceSummaryExecutionCoordinator(
            session_repository=session_repository,
            session_post_processing_job_repository=(
                session_post_processing_job_repository
            ),
            gpu_heavy_execution_gate=gpu_heavy_execution_gate,
            wait_timeout_seconds=wait_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
            gpu_heavy_poll_interval_seconds=gpu_heavy_poll_interval_seconds,
        )

    @property
    def enabled(self) -> bool:
        """workspace summary 생성에 필요한 저장소와 synthesizer가 있는지 반환한다."""

        return self._workspace_summary_store is not None and (
            self._workspace_summary_synthesizer is not None
            or self._workspace_summary_synthesizer_factory is not None
        )

    def save(
        self,
        *,
        session,
        source_version: int,
        utterances,
        correction_document: TranscriptCorrectionDocument | None,
    ) -> None:
        """workspace summary를 생성하고 저장한다. 실패해도 note correction job은 실패시키지 않는다."""

        if self._workspace_summary_store is None:
            return

        synthesizer = self._get_workspace_summary_synthesizer()
        if synthesizer is None:
            return

        self._save_status_safely(
            session_id=session.id,
            source_version=source_version,
            status="processing",
        )
        try:
            with self._hold_execution_slot(
                session_id=session.id,
                source_version=source_version,
            ):
                events = (
                    self._event_repository.list_by_session(session.id)
                    if self._event_repository is not None
                    else []
                )
                summary_document = synthesizer.synthesize(
                    session=session,
                    source_version=source_version,
                    utterances=utterances,
                    correction_document=correction_document,
                    events=events,
                )
                if summary_document is None:
                    self._save_status_safely(
                        session_id=session.id,
                        source_version=source_version,
                        status="completed",
                    )
                    return
                self._workspace_summary_store.save(summary_document)
                self._try_index(summary_document)
        except Exception as error:
            self._save_status_safely(
                session_id=session.id,
                source_version=source_version,
                status="failed",
                error_message=str(error),
            )
            logger.exception(
                "workspace summary 저장 실패: session_id=%s source_version=%s",
                session.id,
                source_version,
            )

    def _get_workspace_summary_synthesizer(self):
        if (
            self._workspace_summary_synthesizer is None
            and self._workspace_summary_synthesizer_factory is not None
        ):
            self._workspace_summary_synthesizer = (
                self._workspace_summary_synthesizer_factory()
            )
        return self._workspace_summary_synthesizer

    def _save_status_safely(
        self,
        *,
        session_id: str,
        source_version: int,
        status: str,
        model: str = "",
        error_message: str | None = None,
    ) -> None:
        if self._workspace_summary_store is None:
            return
        try:
            self._workspace_summary_store.save_status(
                session_id=session_id,
                source_version=source_version,
                status=status,
                model=model,
                error_message=error_message,
            )
        except Exception:
            logger.exception(
                "workspace summary 상태 저장 실패: session_id=%s source_version=%s status=%s",
                session_id,
                source_version,
                status,
            )

    def _try_index(self, summary_document) -> None:
        service = self._workspace_summary_knowledge_indexing_service
        if service is None:
            return
        try:
            service.index_workspace_summary(summary_document)
        except Exception:
            logger.exception(
                "workspace summary knowledge 인덱싱 실패: session_id=%s source_version=%s",
                summary_document.session_id,
                summary_document.source_version,
            )

    def _hold_execution_slot(
        self,
        *,
        session_id: str,
        source_version: int,
    ):
        return self._execution_coordinator.hold(
            session_id=session_id,
            source_version=source_version,
        )
