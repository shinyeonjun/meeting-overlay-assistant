"""노트 correction job 서비스 테스트."""

from server.app.domain.models.utterance import Utterance
from server.app.domain.shared.enums import AudioSource, SessionMode
from server.app.infrastructure.artifacts import LocalArtifactStore
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_note_correction_job_repository import (
    PostgreSQLNoteCorrectionJobRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_utterance_repository import (
    PostgreSQLUtteranceRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.session import (
    PostgreSQLSessionRepository,
)
from server.app.services.reports.jobs.note_correction_job_service import (
    NoteCorrectionJobService,
)
from server.app.services.reports.refinement import (
    TranscriptCorrectionDocument,
    TranscriptCorrectionItem,
    TranscriptCorrectionStore,
)
from server.app.services.sessions.session_service import SessionService
from server.app.services.sessions.workspace_summary_models import (
    WorkspaceSummaryDocument,
)
from server.app.services.sessions.workspace_summary_store import WorkspaceSummaryStore


class _InMemoryQueue:
    def __init__(self) -> None:
        self.job_ids: list[str] = []

    def publish(self, job_id: str) -> bool:
        self.job_ids.append(job_id)
        return True

    def wait_for_job(self, timeout_seconds: float) -> str | None:
        del timeout_seconds
        if not self.job_ids:
            return None
        return self.job_ids.pop(0)


class _StubCorrector:
    def correct(self, *, session_id: str, source_version: int, utterances):
        return TranscriptCorrectionDocument(
            session_id=session_id,
            source_version=source_version,
            model="stub-corrector",
            items=[
                TranscriptCorrectionItem(
                    utterance_id=utterance.id,
                    raw_text=utterance.text,
                    corrected_text=f"{utterance.text} 보정",
                    changed=True,
                    risk_flags=[],
                )
                for utterance in utterances
            ],
        )


class _RecordingReportJobService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None, bool]] = []

    def enqueue_for_session(
        self,
        *,
        session_id: str,
        requested_by_user_id: str | None = None,
        dispatch: bool = True,
    ):
        self.calls.append((session_id, requested_by_user_id, dispatch))
        return None


class _StubWorkspaceSummarySynthesizer:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def synthesize(
        self,
        *,
        session,
        source_version: int,
        utterances,
        correction_document,
        events,
    ):
        del utterances, correction_document, events
        self.calls.append(session.id)
        return WorkspaceSummaryDocument(
            session_id=session.id,
            source_version=source_version,
            model="gemma4:e4b",
            headline="회의 핵심 요약",
            summary=["핵심 요약 문장입니다."],
            decisions=["결정 사항입니다."],
            open_questions=["열린 질문입니다."],
        )


class _SequencedSessionPostProcessingJobRepository:
    def __init__(self, states: list[bool]) -> None:
        self._states = list(states)
        self.calls: list[str | None] = []

    def has_active_processing_jobs(
        self,
        *,
        excluding_session_id: str | None = None,
    ) -> bool:
        self.calls.append(excluding_session_id)
        if self._states:
            return self._states.pop(0)
        return False


class _RecordingGpuExecutionGate:
    class _HoldContext:
        def __init__(self, parent: "_RecordingGpuExecutionGate", owner: str) -> None:
            self._parent = parent
            self._owner = owner

        def __enter__(self) -> None:
            self._parent.calls.append(self._owner)
            return None

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    def __init__(self) -> None:
        self.calls: list[str] = []

    def hold(
        self,
        *,
        owner: str,
        timeout_seconds: float | None = None,
        poll_interval_seconds: float | None = None,
    ):
        del timeout_seconds, poll_interval_seconds
        return self._HoldContext(self, owner)


class TestNoteCorrectionJobService:
    def test_enqueue_for_session은_pending_job을_큐에_발행한다(self, isolated_database):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        repository = PostgreSQLNoteCorrectionJobRepository(isolated_database)
        utterance_repository = PostgreSQLUtteranceRepository(isolated_database)
        session_service = SessionService(session_repository)
        queue = _InMemoryQueue()
        service = NoteCorrectionJobService(
            repository=repository,
            session_repository=session_repository,
            utterance_repository=utterance_repository,
            job_queue=queue,
        )
        session = session_service.create_session_draft(
            title="노트 보정 큐 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )

        job = service.enqueue_for_session(
            session_id=session.id,
            source_version=0,
            requested_by_user_id=None,
            dispatch=True,
        )

        assert queue.job_ids == [job.id]
        assert service.wait_for_dispatched_job(0) == job.id

    def test_live_session이_있으면_workspace_summary_job_claim을_보류한다(
        self,
        isolated_database,
        tmp_path,
    ):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        repository = PostgreSQLNoteCorrectionJobRepository(isolated_database)
        utterance_repository = PostgreSQLUtteranceRepository(isolated_database)
        session_service = SessionService(session_repository)
        workspace_summary_store = WorkspaceSummaryStore(LocalArtifactStore(tmp_path))
        service = NoteCorrectionJobService(
            repository=repository,
            session_repository=session_repository,
            utterance_repository=utterance_repository,
            workspace_summary_synthesizer=_StubWorkspaceSummarySynthesizer(),
            workspace_summary_store=workspace_summary_store,
        )
        target_session = session_service.create_session_draft(
            title="요약 대기 대상",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        target_session = session_service.start_session(target_session.id)
        target_session = session_service.end_session(target_session.id)
        job = service.enqueue_for_session(
            session_id=target_session.id,
            source_version=target_session.canonical_transcript_version,
            requested_by_user_id=None,
            dispatch=False,
        )
        live_session = session_service.create_session_draft(
            title="진행 중인 실시간 세션",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        session_service.start_session(live_session.id)

        claimed_jobs = service.claim_available_jobs(
            worker_id="worker-a",
            lease_duration_seconds=120,
            limit=1,
        )

        assert claimed_jobs == []
        assert repository.get_by_id(job.id).status == "pending"

    def test_live_session이_있어도_heavy_work가_없으면_job을_claim한다(
        self,
        isolated_database,
    ):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        repository = PostgreSQLNoteCorrectionJobRepository(isolated_database)
        utterance_repository = PostgreSQLUtteranceRepository(isolated_database)
        session_service = SessionService(session_repository)
        service = NoteCorrectionJobService(
            repository=repository,
            session_repository=session_repository,
            utterance_repository=utterance_repository,
        )
        target_session = session_service.create_session_draft(
            title="가벼운 note job 대상",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        target_session = session_service.start_session(target_session.id)
        target_session = session_service.end_session(target_session.id)
        job = service.enqueue_for_session(
            session_id=target_session.id,
            source_version=target_session.canonical_transcript_version,
            requested_by_user_id=None,
            dispatch=False,
        )
        live_session = session_service.create_session_draft(
            title="진행 중인 실시간 세션",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        session_service.start_session(live_session.id)

        claimed_jobs = service.claim_available_jobs(
            worker_id="worker-a",
            lease_duration_seconds=120,
            limit=1,
        )

        assert [claimed_job.id for claimed_job in claimed_jobs] == [job.id]
        assert repository.get_by_id(job.id).status == "processing"

    def test_process_job은_correction을_저장하고_report_job을_연결한다(
        self,
        isolated_database,
        tmp_path,
    ):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        repository = PostgreSQLNoteCorrectionJobRepository(isolated_database)
        utterance_repository = PostgreSQLUtteranceRepository(isolated_database)
        session_service = SessionService(session_repository)
        artifact_store = LocalArtifactStore(tmp_path)
        correction_store = TranscriptCorrectionStore(artifact_store)
        report_job_service = _RecordingReportJobService()

        session = session_service.create_session_draft(
            title="노트 보정 처리 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        session = session_service.start_session(session.id)
        session = session_service.end_session(session.id)
        session = session_repository.save(session.mark_post_processing_completed())

        utterance_repository.save(
            Utterance.create(
                session_id=session.id,
                seq_num=1,
                start_ms=0,
                end_ms=1000,
                text="원본 발화",
                confidence=0.91,
                input_source="system_audio",
                speaker_label="SPEAKER_00",
                transcript_source="post_processed",
                processing_job_id="post-job-1",
            )
        )

        service = NoteCorrectionJobService(
            repository=repository,
            session_repository=session_repository,
            utterance_repository=utterance_repository,
            note_transcript_corrector=_StubCorrector(),
            transcript_correction_store=correction_store,
            report_generation_job_service=report_job_service,
        )

        job = service.enqueue_for_session(
            session_id=session.id,
            source_version=1,
            dispatch=False,
        )
        processed_job = service.process_job(job.id)
        document = correction_store.load(
            session_id=session.id,
            expected_source_version=1,
        )

        assert processed_job.status == "completed"
        assert document is not None
        assert document.model == "stub-corrector"
        assert [item.corrected_text for item in document.items] == ["원본 발화 보정"]
        assert report_job_service.calls == [(session.id, None, True)]

    def test_stale_source_version_job은_건너뛰고_report를_생성하지_않는다(
        self,
        isolated_database,
        tmp_path,
    ):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        repository = PostgreSQLNoteCorrectionJobRepository(isolated_database)
        utterance_repository = PostgreSQLUtteranceRepository(isolated_database)
        session_service = SessionService(session_repository)
        artifact_store = LocalArtifactStore(tmp_path)
        correction_store = TranscriptCorrectionStore(artifact_store)
        report_job_service = _RecordingReportJobService()

        session = session_service.create_session_draft(
            title="stale correction 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        session = session_service.start_session(session.id)
        session = session_service.end_session(session.id)
        session = session_repository.save(session.mark_post_processing_completed())

        service = NoteCorrectionJobService(
            repository=repository,
            session_repository=session_repository,
            utterance_repository=utterance_repository,
            note_transcript_corrector=_StubCorrector(),
            transcript_correction_store=correction_store,
            report_generation_job_service=report_job_service,
        )

        stale_job = service.enqueue_for_session(
            session_id=session.id,
            source_version=0,
            dispatch=False,
        )
        processed_job = service.process_job(stale_job.id)

        assert processed_job.status == "completed"
        assert correction_store.load(session_id=session.id) is None
        assert report_job_service.calls == []

    def test_process_job은_workspace_summary를_artifact로_저장한다(
        self,
        isolated_database,
        tmp_path,
    ):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        repository = PostgreSQLNoteCorrectionJobRepository(isolated_database)
        utterance_repository = PostgreSQLUtteranceRepository(isolated_database)
        session_service = SessionService(session_repository)
        artifact_store = LocalArtifactStore(tmp_path)
        correction_store = TranscriptCorrectionStore(artifact_store)
        workspace_summary_store = WorkspaceSummaryStore(artifact_store)
        report_job_service = _RecordingReportJobService()
        synthesizer = _StubWorkspaceSummarySynthesizer()

        session = session_service.create_session_draft(
            title="workspace summary 저장 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        session = session_service.start_session(session.id)
        session = session_service.end_session(session.id)
        session = session_repository.save(session.mark_post_processing_completed())

        utterance_repository.save(
            Utterance.create(
                session_id=session.id,
                seq_num=1,
                start_ms=0,
                end_ms=1000,
                text="요약 대상 발화",
                confidence=0.91,
                input_source="system_audio",
                speaker_label="SPEAKER_00",
                transcript_source="post_processed",
                processing_job_id="post-job-1",
            )
        )

        service = NoteCorrectionJobService(
            repository=repository,
            session_repository=session_repository,
            utterance_repository=utterance_repository,
            note_transcript_corrector=_StubCorrector(),
            transcript_correction_store=correction_store,
            workspace_summary_synthesizer=synthesizer,
            workspace_summary_store=workspace_summary_store,
            report_generation_job_service=report_job_service,
        )

        job = service.enqueue_for_session(
            session_id=session.id,
            source_version=1,
            dispatch=False,
        )
        processed_job = service.process_job(job.id)
        summary_document = workspace_summary_store.load(
            session_id=session.id,
            expected_source_version=1,
        )

        assert processed_job.status == "completed"
        assert summary_document is not None
        assert summary_document.headline == "회의 핵심 요약"
        assert summary_document.summary == ["핵심 요약 문장입니다."]
        assert summary_document.decisions == ["결정 사항입니다."]
        assert synthesizer.calls == [session.id]

    def test_workspace_summary는_다른_post_processing이_끝날때까지_잠깐_기다린다(
        self,
        isolated_database,
        tmp_path,
    ):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        repository = PostgreSQLNoteCorrectionJobRepository(isolated_database)
        utterance_repository = PostgreSQLUtteranceRepository(isolated_database)
        session_service = SessionService(session_repository)
        artifact_store = LocalArtifactStore(tmp_path)
        correction_store = TranscriptCorrectionStore(artifact_store)
        workspace_summary_store = WorkspaceSummaryStore(artifact_store)
        report_job_service = _RecordingReportJobService()
        synthesizer = _StubWorkspaceSummarySynthesizer()
        processing_repository = _SequencedSessionPostProcessingJobRepository([True, False])

        session = session_service.create_session_draft(
            title="workspace summary 대기 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        session = session_service.start_session(session.id)
        session = session_service.end_session(session.id)
        session = session_repository.save(session.mark_post_processing_completed())

        utterance_repository.save(
            Utterance.create(
                session_id=session.id,
                seq_num=1,
                start_ms=0,
                end_ms=1000,
                text="대기 후 요약할 발화",
                confidence=0.91,
                input_source="system_audio",
                speaker_label="SPEAKER_00",
                transcript_source="post_processed",
                processing_job_id="post-job-1",
            )
        )

        service = NoteCorrectionJobService(
            repository=repository,
            session_repository=session_repository,
            utterance_repository=utterance_repository,
            note_transcript_corrector=_StubCorrector(),
            transcript_correction_store=correction_store,
            workspace_summary_synthesizer=synthesizer,
            workspace_summary_store=workspace_summary_store,
            session_post_processing_job_repository=processing_repository,
            workspace_summary_wait_timeout_seconds=1.0,
            workspace_summary_poll_interval_seconds=0.01,
            report_generation_job_service=report_job_service,
        )

        job = service.enqueue_for_session(
            session_id=session.id,
            source_version=1,
            dispatch=False,
        )
        processed_job = service.process_job(job.id)
        summary_document = workspace_summary_store.load(
            session_id=session.id,
            expected_source_version=1,
        )

        assert processed_job.status == "completed"
        assert summary_document is not None
        assert synthesizer.calls == [session.id]

    def test_workspace_summary는_running_session이_끝날때까지_잠깐_기다린다(
        self,
        isolated_database,
        tmp_path,
        monkeypatch,
    ):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        repository = PostgreSQLNoteCorrectionJobRepository(isolated_database)
        utterance_repository = PostgreSQLUtteranceRepository(isolated_database)
        session_service = SessionService(session_repository)
        artifact_store = LocalArtifactStore(tmp_path)
        correction_store = TranscriptCorrectionStore(artifact_store)
        workspace_summary_store = WorkspaceSummaryStore(artifact_store)
        report_job_service = _RecordingReportJobService()
        synthesizer = _StubWorkspaceSummarySynthesizer()
        running_counts = [1, 0]
        observed_counts: list[int] = []

        session = session_service.create_session_draft(
            title="workspace summary live 대기 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        session = session_service.start_session(session.id)
        session = session_service.end_session(session.id)
        session = session_repository.save(session.mark_post_processing_completed())

        utterance_repository.save(
            Utterance.create(
                session_id=session.id,
                seq_num=1,
                start_ms=0,
                end_ms=1000,
                text="live 종료 뒤 요약할 발화",
                confidence=0.91,
                input_source="system_audio",
                speaker_label="SPEAKER_00",
                transcript_source="post_processed",
                processing_job_id="post-job-1",
            )
        )

        def fake_count_running() -> int:
            value = running_counts.pop(0) if running_counts else 0
            observed_counts.append(value)
            return value

        monkeypatch.setattr(session_repository, "count_running", fake_count_running)

        service = NoteCorrectionJobService(
            repository=repository,
            session_repository=session_repository,
            utterance_repository=utterance_repository,
            note_transcript_corrector=_StubCorrector(),
            transcript_correction_store=correction_store,
            workspace_summary_synthesizer=synthesizer,
            workspace_summary_store=workspace_summary_store,
            workspace_summary_wait_timeout_seconds=1.0,
            workspace_summary_poll_interval_seconds=0.01,
            report_generation_job_service=report_job_service,
        )

        job = service.enqueue_for_session(
            session_id=session.id,
            source_version=1,
            dispatch=False,
        )
        processed_job = service.process_job(job.id)
        summary_document = workspace_summary_store.load(
            session_id=session.id,
            expected_source_version=1,
        )

        assert processed_job.status == "completed"
        assert summary_document is not None
        assert synthesizer.calls == [session.id]
        assert observed_counts == [1, 0]

    def test_workspace_summary는_gpu_gate를_우선_획득한다(
        self,
        isolated_database,
        tmp_path,
    ):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        repository = PostgreSQLNoteCorrectionJobRepository(isolated_database)
        utterance_repository = PostgreSQLUtteranceRepository(isolated_database)
        session_service = SessionService(session_repository)
        artifact_store = LocalArtifactStore(tmp_path)
        correction_store = TranscriptCorrectionStore(artifact_store)
        workspace_summary_store = WorkspaceSummaryStore(artifact_store)
        report_job_service = _RecordingReportJobService()
        synthesizer = _StubWorkspaceSummarySynthesizer()
        processing_repository = _SequencedSessionPostProcessingJobRepository([True, True])
        gpu_gate = _RecordingGpuExecutionGate()

        session = session_service.create_session_draft(
            title="workspace summary gate 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        session = session_service.start_session(session.id)
        session = session_service.end_session(session.id)
        session = session_repository.save(session.mark_post_processing_completed())

        utterance_repository.save(
            Utterance.create(
                session_id=session.id,
                seq_num=1,
                start_ms=0,
                end_ms=1000,
                text="gate 기반 summary 발화",
                confidence=0.91,
                input_source="system_audio",
                speaker_label="SPEAKER_00",
                transcript_source="post_processed",
                processing_job_id="post-job-1",
            )
        )

        service = NoteCorrectionJobService(
            repository=repository,
            session_repository=session_repository,
            utterance_repository=utterance_repository,
            note_transcript_corrector=_StubCorrector(),
            transcript_correction_store=correction_store,
            workspace_summary_synthesizer=synthesizer,
            workspace_summary_store=workspace_summary_store,
            session_post_processing_job_repository=processing_repository,
            gpu_heavy_execution_gate=gpu_gate,
            report_generation_job_service=report_job_service,
        )

        job = service.enqueue_for_session(
            session_id=session.id,
            source_version=1,
            dispatch=False,
        )
        processed_job = service.process_job(job.id)
        summary_document = workspace_summary_store.load(
            session_id=session.id,
            expected_source_version=1,
        )

        assert processed_job.status == "completed"
        assert summary_document is not None
        assert synthesizer.calls == [session.id]
        assert gpu_gate.calls == [f"workspace_summary:{session.id}:1"]
        assert processing_repository.calls == []

    def test_workspace_summary는_live_대기시간이_초과돼도_기존흐름으로_저장한다(
        self,
        isolated_database,
        tmp_path,
        monkeypatch,
    ):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        repository = PostgreSQLNoteCorrectionJobRepository(isolated_database)
        utterance_repository = PostgreSQLUtteranceRepository(isolated_database)
        session_service = SessionService(session_repository)
        artifact_store = LocalArtifactStore(tmp_path)
        correction_store = TranscriptCorrectionStore(artifact_store)
        workspace_summary_store = WorkspaceSummaryStore(artifact_store)
        report_job_service = _RecordingReportJobService()
        synthesizer = _StubWorkspaceSummarySynthesizer()
        observed_counts: list[int] = []

        session = session_service.create_session_draft(
            title="workspace summary live timeout 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        session = session_service.start_session(session.id)
        session = session_service.end_session(session.id)
        session = session_repository.save(session.mark_post_processing_completed())

        utterance_repository.save(
            Utterance.create(
                session_id=session.id,
                seq_num=1,
                start_ms=0,
                end_ms=1000,
                text="live timeout 이후에도 저장할 발화",
                confidence=0.91,
                input_source="system_audio",
                speaker_label="SPEAKER_00",
                transcript_source="post_processed",
                processing_job_id="post-job-1",
            )
        )

        def fake_count_running() -> int:
            observed_counts.append(1)
            return 1

        monkeypatch.setattr(session_repository, "count_running", fake_count_running)

        service = NoteCorrectionJobService(
            repository=repository,
            session_repository=session_repository,
            utterance_repository=utterance_repository,
            note_transcript_corrector=_StubCorrector(),
            transcript_correction_store=correction_store,
            workspace_summary_synthesizer=synthesizer,
            workspace_summary_store=workspace_summary_store,
            workspace_summary_wait_timeout_seconds=0.0,
            workspace_summary_poll_interval_seconds=0.01,
            report_generation_job_service=report_job_service,
        )

        job = service.enqueue_for_session(
            session_id=session.id,
            source_version=1,
            dispatch=False,
        )
        processed_job = service.process_job(job.id)
        summary_document = workspace_summary_store.load(
            session_id=session.id,
            expected_source_version=1,
        )

        assert processed_job.status == "completed"
        assert summary_document is not None
        assert synthesizer.calls == [session.id]
        assert observed_counts == [1]

    def test_workspace_summary는_대기시간이_초과돼도_기존흐름으로_저장한다(
        self,
        isolated_database,
        tmp_path,
    ):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        repository = PostgreSQLNoteCorrectionJobRepository(isolated_database)
        utterance_repository = PostgreSQLUtteranceRepository(isolated_database)
        session_service = SessionService(session_repository)
        artifact_store = LocalArtifactStore(tmp_path)
        correction_store = TranscriptCorrectionStore(artifact_store)
        workspace_summary_store = WorkspaceSummaryStore(artifact_store)
        report_job_service = _RecordingReportJobService()
        synthesizer = _StubWorkspaceSummarySynthesizer()
        processing_repository = _SequencedSessionPostProcessingJobRepository([True, True, True])

        session = session_service.create_session_draft(
            title="workspace summary timeout 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        session = session_service.start_session(session.id)
        session = session_service.end_session(session.id)
        session = session_repository.save(session.mark_post_processing_completed())

        utterance_repository.save(
            Utterance.create(
                session_id=session.id,
                seq_num=1,
                start_ms=0,
                end_ms=1000,
                text="timeout 이후에도 요약할 발화",
                confidence=0.91,
                input_source="system_audio",
                speaker_label="SPEAKER_00",
                transcript_source="post_processed",
                processing_job_id="post-job-1",
            )
        )

        service = NoteCorrectionJobService(
            repository=repository,
            session_repository=session_repository,
            utterance_repository=utterance_repository,
            note_transcript_corrector=_StubCorrector(),
            transcript_correction_store=correction_store,
            workspace_summary_synthesizer=synthesizer,
            workspace_summary_store=workspace_summary_store,
            session_post_processing_job_repository=processing_repository,
            workspace_summary_wait_timeout_seconds=0.0,
            workspace_summary_poll_interval_seconds=0.01,
            report_generation_job_service=report_job_service,
        )

        job = service.enqueue_for_session(
            session_id=session.id,
            source_version=1,
            dispatch=False,
        )
        processed_job = service.process_job(job.id)
        summary_document = workspace_summary_store.load(
            session_id=session.id,
            expected_source_version=1,
        )

        assert processed_job.status == "completed"
        assert summary_document is not None
        assert synthesizer.calls == [session.id]
