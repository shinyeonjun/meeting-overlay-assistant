"""공통 영역의 session post processing job service 서비스를 제공한다."""

from __future__ import annotations

from collections.abc import Callable

from server.app.core.config import settings
from server.app.contexts.insight import MeetingAnalyzer, MeetingEvent
from server.app.contexts.post_processing.application.session_post_processing_builders import (
    build_canonical_events,
    build_canonical_utterances,
)
from server.app.contexts.post_processing.application.session_post_processing_canonical_state import (
    CanonicalStateSnapshot,
    CanonicalTranscriptState,
)
from server.app.contexts.post_processing.application.session_post_processing_dispatch import (
    SessionPostProcessingDispatchMixin,
)
from server.app.contexts.post_processing.application.session_post_processing_runner import (
    SessionPostProcessingRunMixin,
)
from server.app.domain.models.utterance import Utterance
from server.app.infrastructure.artifacts import LocalArtifactStore
from server.app.repositories.contracts.events.event_repository import (
    MeetingEventRepository,
)
from server.app.repositories.contracts.session import SessionRepository
from server.app.repositories.contracts.session_post_processing_job_repository import (
    SessionPostProcessingJobRepository,
)
from server.app.repositories.contracts.utterance_repository import UtteranceRepository
from server.app.contexts.insight import MeetingEventService
from server.app.contexts.post_processing.application.session_post_processing_job_queue import (
    SessionPostProcessingJobQueue,
)
from server.app.workers.job_claim_fence import (
    ensure_claim_held,
    is_claim_held,
    write_claimed_job,
)
from server.app.contexts.reporting import (
    AudioPostprocessingService,
)
from server.app.contexts.reporting import (
    NoteCorrectionJobService,
)
from server.app.contexts.reporting import (
    TranscriptCorrectionStore,
)


class SessionPostProcessingJobService(
    SessionPostProcessingDispatchMixin,
    SessionPostProcessingRunMixin,
):
    """녹음 아티팩트 기준으로 세션 후처리 파이프라인을 실행한다.

    이 서비스는 raw 오디오를 다시 읽어 transcript/event를 재생성하고,
    이후 단계인 note correction과 report generation으로 흐름을 넘긴다.

    enqueue·dispatch·lease·조회는 `SessionPostProcessingDispatchMixin`,
    job 실행 파이프라인은 `SessionPostProcessingRunMixin`에 있고,
    canonical 상태 교체·복구는 `CanonicalTranscriptState`가 맡는다.
    """

    def __init__(
        self,
        *,
        repository: SessionPostProcessingJobRepository,
        session_repository: SessionRepository,
        utterance_repository: UtteranceRepository | None = None,
        event_repository: MeetingEventRepository | None = None,
        audio_postprocessing_service: (
            AudioPostprocessingService | Callable[[], AudioPostprocessingService] | None
        ) = None,
        analyzer: MeetingAnalyzer | Callable[[], MeetingAnalyzer] | None = None,
        note_correction_job_service: (
            NoteCorrectionJobService | Callable[[], NoteCorrectionJobService | None] | None
        ) = None,
        job_queue: SessionPostProcessingJobQueue | None = None,
        artifact_store: LocalArtifactStore | None = None,
        transcript_correction_store: TranscriptCorrectionStore | None = None,
        database=None,
    ) -> None:
        self._repository = repository
        self._session_repository = session_repository
        self._utterance_repository = utterance_repository
        self._event_repository = event_repository
        self._audio_postprocessing_service = (
            None if callable(audio_postprocessing_service) else audio_postprocessing_service
        )
        self._audio_postprocessing_service_factory = (
            audio_postprocessing_service if callable(audio_postprocessing_service) else None
        )
        self._analyzer = None if callable(analyzer) else analyzer
        self._analyzer_factory = analyzer if callable(analyzer) else None
        self._note_correction_job_service = (
            None if callable(note_correction_job_service) else note_correction_job_service
        )
        self._note_correction_job_service_factory = (
            note_correction_job_service if callable(note_correction_job_service) else None
        )
        self._job_queue = job_queue
        self._artifact_store = artifact_store or LocalArtifactStore(settings.artifacts_root_path)
        self._event_service = MeetingEventService(event_repository) if event_repository is not None else None
        self._canonical_state = CanonicalTranscriptState(
            utterance_repository=utterance_repository,
            event_repository=event_repository,
            event_service=self._event_service,
            transcript_correction_store=transcript_correction_store,
            database=database,
        )

    def _is_claim_held(self, job_id: str, worker_id: str | None) -> bool:
        return is_claim_held(self._repository, job_id, worker_id)

    def _ensure_claim_held(self, job, worker_id: str | None) -> None:
        ensure_claim_held(self._repository, job, worker_id)

    def _write_terminal_job(self, job, worker_id: str | None):
        return write_claimed_job(self._repository, job, worker_id)

    def _build_canonical_utterances(
        self,
        *,
        session_id: str,
        input_source: str,
        processing_job_id: str,
        speaker_transcript,
    ) -> list[Utterance]:
        return build_canonical_utterances(
            session_id=session_id,
            input_source=input_source,
            processing_job_id=processing_job_id,
            speaker_transcript=speaker_transcript,
        )

    def _build_canonical_events(
        self,
        *,
        utterances: list[Utterance],
        processing_job_id: str,
    ) -> list[MeetingEvent]:
        return build_canonical_events(
            analyzer=self._get_analyzer(),
            utterances=utterances,
            processing_job_id=processing_job_id,
        )

    def _snapshot_canonical_state(self, session_id: str) -> CanonicalStateSnapshot:
        return self._canonical_state.snapshot(session_id)

    def _replace_canonical_state(
        self,
        *,
        session_id: str,
        utterances: list[Utterance],
        events: list[MeetingEvent],
    ) -> None:
        self._canonical_state.replace(
            session_id=session_id,
            utterances=utterances,
            events=events,
        )

    def _discard_provisional_transcript(self, session_id: str) -> None:
        self._canonical_state.discard_provisional(session_id)

    def _restore_canonical_state(
        self,
        *,
        session_id: str,
        snapshot: CanonicalStateSnapshot,
    ) -> None:
        self._canonical_state.restore(session_id=session_id, snapshot=snapshot)

    def _ensure_processing_dependencies(self) -> None:
        if self._utterance_repository is None:
            raise RuntimeError("후처리용 utterance repository가 필요합니다.")
        if self._event_repository is None or self._event_service is None:
            raise RuntimeError("후처리용 event repository가 필요합니다.")
        if self._audio_postprocessing_service is None and self._audio_postprocessing_service_factory is None:
            raise RuntimeError("후처리용 audio_postprocessing_service가 필요합니다.")

    def _get_audio_postprocessing_service(self) -> AudioPostprocessingService:
        if self._audio_postprocessing_service is None:
            if self._audio_postprocessing_service_factory is None:
                raise RuntimeError("후처리용 audio_postprocessing_service가 필요합니다.")
            self._audio_postprocessing_service = self._audio_postprocessing_service_factory()
        return self._audio_postprocessing_service

    def _get_analyzer(self) -> MeetingAnalyzer | None:
        if self._analyzer is None and self._analyzer_factory is not None:
            self._analyzer = self._analyzer_factory()
        return self._analyzer

    def _get_note_correction_job_service(self) -> NoteCorrectionJobService | None:
        if self._note_correction_job_service is None and self._note_correction_job_service_factory is not None:
            self._note_correction_job_service = self._note_correction_job_service_factory()
        return self._note_correction_job_service
