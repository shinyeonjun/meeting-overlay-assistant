"""세션 영역의 test session post processing job service 동작을 검증한다."""
from __future__ import annotations

from server.app.domain.events import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.domain.shared.enums import AudioSource, EventState, EventType, SessionMode
from server.app.infrastructure.artifacts import LocalArtifactStore
from server.app.infrastructure.persistence.postgresql.repositories.events.postgresql_event_repository import (
    PostgreSQLMeetingEventRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_session_post_processing_job_repository import (
    PostgreSQLSessionPostProcessingJobRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_utterance_repository import (
    PostgreSQLUtteranceRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.session import (
    PostgreSQLSessionRepository,
)
from server.app.services.post_meeting.session_post_processing_job_service import (
    SessionPostProcessingJobService,
)
from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)
from server.app.services.reports.refinement import TranscriptCorrectionStore
from server.app.services.sessions.session_service import SessionService


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


class _StubAudioPostprocessingService:
    def build_speaker_transcript(self, audio_path, *, on_segment=None):
        del audio_path
        segments = [
            SpeakerTranscriptSegment(
                speaker_label="SPEAKER_00",
                start_ms=0,
                end_ms=1200,
                text="결정은 다음 주에 다시 논의합시다",
                confidence=0.93,
            ),
            SpeakerTranscriptSegment(
                speaker_label="SPEAKER_01",
                start_ms=1200,
                end_ms=2600,
                text="질문은 예산안을 누가 정리할까요?",
                confidence=0.91,
            ),
        ]
        if on_segment is not None:
            for segment in segments:
                on_segment(segment)
        return segments


class _InspectingAudioPostprocessingService:
    def __init__(self, inspect_callback) -> None:
        self._inspect_callback = inspect_callback

    def build_speaker_transcript(self, audio_path, *, on_segment=None):
        segments = _StubAudioPostprocessingService().build_speaker_transcript(audio_path)
        if on_segment is not None:
            for index, segment in enumerate(segments, start=1):
                on_segment(segment)
                self._inspect_callback(index)
        return segments


class _StubAnalyzer:
    def analyze(self, utterance):
        event_type = EventType.QUESTION if "질문" in utterance.text else EventType.DECISION
        state = EventState.OPEN if event_type == EventType.QUESTION else EventState.CONFIRMED
        return [
            MeetingEvent.create(
                session_id=utterance.session_id,
                event_type=event_type,
                title=utterance.text,
                state=state,
                source_utterance_id=utterance.id,
                evidence_text=utterance.text,
                speaker_label=utterance.speaker_label,
                input_source=utterance.input_source,
            )
        ]


class _RecordingNoteCorrectionJobService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, str | None, bool]] = []

    def enqueue_for_session(
        self,
        *,
        session_id: str,
        source_version: int,
        requested_by_user_id: str | None = None,
        dispatch: bool = True,
    ):
        self.calls.append((session_id, source_version, requested_by_user_id, dispatch))
        return None


class _FailingNoteCorrectionJobService:
    def enqueue_for_session(
        self,
        *,
        session_id: str,
        source_version: int,
        requested_by_user_id: str | None = None,
        dispatch: bool = True,
    ):
        del session_id, source_version, requested_by_user_id, dispatch
        raise RuntimeError("note correction enqueue failed")


class _StubNoteTranscriptCorrector:
    def correct(self, *, session_id: str, source_version: int, utterances):
        from server.app.services.reports.refinement import (
            TranscriptCorrectionDocument,
            TranscriptCorrectionItem,
        )

        items = []
        for utterance in utterances:
            items.append(
                TranscriptCorrectionItem(
                    utterance_id=utterance.id,
                    raw_text=utterance.text,
                    corrected_text=utterance.text.replace("기존", "결정"),
                    changed="기존" in utterance.text,
                    risk_flags=[],
                )
            )
        return TranscriptCorrectionDocument(
            session_id=session_id,
            source_version=source_version,
            model="stub-gemma",
            items=items,
        )


class TestSessionPostProcessingJobService:
    """dispatch와 claim/lease 계약을 검증한다."""

    def test_enqueue_for_session은_pending_job을_queue에_발행한다(self, isolated_database):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        repository = PostgreSQLSessionPostProcessingJobRepository(isolated_database)
        queue = _InMemoryQueue()
        session_service = SessionService(session_repository)
        service = SessionPostProcessingJobService(
            repository=repository,
            session_repository=session_repository,
            job_queue=queue,
        )
        session = session_service.create_session_draft(
            title="후처리 큐 발행 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )

        job = service.enqueue_for_session(
            session_id=session.id,
            requested_by_user_id=None,
            dispatch=True,
        )

        assert queue.job_ids == [job.id]
        assert service.wait_for_dispatched_job(0) == job.id
        refreshed_session = session_service.get_session(session.id)
        assert refreshed_session is not None
        assert refreshed_session.post_processing_status == "queued"

    def test_worker가_pending_job을_claim하면_lease와_attempt가_기록된다(
        self,
        isolated_database,
    ):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        repository = PostgreSQLSessionPostProcessingJobRepository(isolated_database)
        session_service = SessionService(session_repository)
        service = SessionPostProcessingJobService(
            repository=repository,
            session_repository=session_repository,
        )
        session = session_service.create_session_draft(
            title="후처리 분산 처리 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        service.enqueue_for_session(
            session_id=session.id,
            requested_by_user_id=None,
            dispatch=False,
        )

        claimed_jobs = service.claim_available_jobs(
            worker_id="worker-a",
            lease_duration_seconds=120,
            limit=1,
        )

        assert len(claimed_jobs) == 1
        claimed_job = claimed_jobs[0]
        assert claimed_job.status == "processing"
        assert claimed_job.claimed_by_worker_id == "worker-a"
        assert claimed_job.lease_expires_at is not None
        assert claimed_job.attempt_count == 1

    def test_process_job은_canonical_utterance와_event를_저장하고_note_correction으로_연결한다(
        self,
        isolated_database,
        tmp_path,
    ):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        job_repository = PostgreSQLSessionPostProcessingJobRepository(isolated_database)
        utterance_repository = PostgreSQLUtteranceRepository(isolated_database)
        event_repository = PostgreSQLMeetingEventRepository(isolated_database)
        note_correction_job_service = _RecordingNoteCorrectionJobService()
        session_service = SessionService(session_repository)
        artifact_store = LocalArtifactStore(tmp_path)
        correction_store = TranscriptCorrectionStore(artifact_store)

        session = session_service.create_session_draft(
            title="후처리 처리 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        session = session_service.start_session(session.id)
        session = session_service.end_session(session.id)

        recording_artifact = artifact_store.build_recording_artifact(
            session_id=session.id,
            input_source="system_audio",
        )
        recording_artifact.file_path.parent.mkdir(parents=True, exist_ok=True)
        recording_artifact.file_path.write_bytes(b"RIFF0000WAVEfmt ")

        service = SessionPostProcessingJobService(
            repository=job_repository,
            session_repository=session_repository,
            utterance_repository=utterance_repository,
            event_repository=event_repository,
            audio_postprocessing_service=_StubAudioPostprocessingService(),
            analyzer=_StubAnalyzer(),
            note_correction_job_service=note_correction_job_service,
            artifact_store=artifact_store,
            transcript_correction_store=correction_store,
        )

        job = service.enqueue_for_session(
            session_id=session.id,
            requested_by_user_id=None,
            dispatch=False,
        )
        processed_job = service.process_job(job.id)

        refreshed_session = session_service.get_session(session.id)
        utterances = utterance_repository.list_by_session(session.id)
        events = event_repository.list_by_session(session.id)
        correction_document = correction_store.load(session_id=session.id)

        assert processed_job.status == "completed"
        assert refreshed_session is not None
        assert refreshed_session.post_processing_status == "completed"
        assert refreshed_session.canonical_transcript_version == 1
        assert refreshed_session.canonical_events_version == 1
        assert [item.transcript_source for item in utterances] == [
            "post_processed",
            "post_processed",
        ]
        assert [item.speaker_label for item in utterances] == [
            "SPEAKER_00",
            "SPEAKER_01",
        ]
        assert {item.event_source for item in events} == {"post_processed"}
        assert {item.event_type for item in events} == {
            EventType.DECISION,
            EventType.QUESTION,
        }
        assert correction_document is None
        assert note_correction_job_service.calls == [(session.id, 1, None, True)]

    def test_processing_중인_job이_있으면_세션을_다시_queued로_돌리지_않는다(
        self,
        isolated_database,
    ):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        repository = PostgreSQLSessionPostProcessingJobRepository(isolated_database)
        session_service = SessionService(session_repository)
        service = SessionPostProcessingJobService(
            repository=repository,
            session_repository=session_repository,
        )
        session = session_service.create_session_draft(
            title="중복 reprocess 방지 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        session = session_service.start_session(session.id)
        session = session_service.end_session(session.id)

        pending_job = service.enqueue_for_session(
            session_id=session.id,
            requested_by_user_id=None,
            dispatch=False,
        )
        processing_job = service.claim_available_jobs(
            worker_id="worker-a",
            lease_duration_seconds=120,
            limit=1,
        )[0]
        current_session = session_service.get_session(session.id)
        assert current_session is not None
        session_repository.save(
            current_session.mark_post_processing_started(
                recording_artifact_id=pending_job.recording_artifact_id,
            )
        )

        returned_job = service.enqueue_for_session(
            session_id=session.id,
            requested_by_user_id=None,
            dispatch=False,
        )

        refreshed_session = session_service.get_session(session.id)
        assert returned_job.id == processing_job.id
        assert refreshed_session is not None
        assert refreshed_session.post_processing_status == "processing"
        assert repository.list_pending(limit=10) == []

    def test_report_enqueue_실패시_기존_canonical_state를_복구한다(
        self,
        isolated_database,
        tmp_path,
    ):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        job_repository = PostgreSQLSessionPostProcessingJobRepository(isolated_database)
        utterance_repository = PostgreSQLUtteranceRepository(isolated_database)
        event_repository = PostgreSQLMeetingEventRepository(isolated_database)
        session_service = SessionService(session_repository)
        artifact_store = LocalArtifactStore(tmp_path)
        correction_store = TranscriptCorrectionStore(artifact_store)

        session = session_service.create_session_draft(
            title="복구 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        session = session_service.start_session(session.id)
        session = session_service.end_session(session.id)

        existing_utterance = utterance_repository.save(
            Utterance.create(
                session_id=session.id,
                seq_num=1,
                start_ms=0,
                end_ms=1000,
                text="기존 발화",
                confidence=0.88,
                input_source="system_audio",
                speaker_label="SPEAKER_09",
                transcript_source="post_processed",
                processing_job_id="job-existing",
            )
        )
        event_repository.save(
            MeetingEvent.create(
                session_id=session.id,
                event_type=EventType.DECISION,
                title="기존 이벤트",
                state=EventState.CONFIRMED,
                source_utterance_id=existing_utterance.id,
                evidence_text="기존 이벤트",
                speaker_label="SPEAKER_09",
                input_source="system_audio",
                event_source="post_processed",
                processing_job_id="job-existing",
            )
        )
        correction_store.save(
            _StubNoteTranscriptCorrector().correct(
                session_id=session.id,
                source_version=1,
                utterances=[existing_utterance],
            )
        )

        recording_artifact = artifact_store.build_recording_artifact(
            session_id=session.id,
            input_source="system_audio",
        )
        recording_artifact.file_path.parent.mkdir(parents=True, exist_ok=True)
        recording_artifact.file_path.write_bytes(b"RIFF0000WAVEfmt ")

        service = SessionPostProcessingJobService(
            repository=job_repository,
            session_repository=session_repository,
            utterance_repository=utterance_repository,
            event_repository=event_repository,
            audio_postprocessing_service=_StubAudioPostprocessingService(),
            analyzer=_StubAnalyzer(),
            note_correction_job_service=_FailingNoteCorrectionJobService(),
            artifact_store=artifact_store,
            transcript_correction_store=correction_store,
        )

        job = service.enqueue_for_session(
            session_id=session.id,
            requested_by_user_id=None,
            dispatch=False,
        )
        processed_job = service.process_job(job.id)

        restored_session = session_service.get_session(session.id)
        restored_utterances = utterance_repository.list_by_session(session.id)
        restored_events = event_repository.list_by_session(session.id)
        restored_correction = correction_store.load(session_id=session.id)

        assert processed_job.status == "failed"
        assert restored_session is not None
        assert restored_session.post_processing_status == "failed"
        assert [item.text for item in restored_utterances] == ["기존 발화"]
        assert [item.title for item in restored_events] == ["기존 이벤트"]
        assert restored_correction is not None
        assert [item.corrected_text for item in restored_correction.items] == ["결정 발화"]

    def test_process_job은_진행중에_provisional_transcript를_누적_저장한다(
        self,
        isolated_database,
        tmp_path,
    ):
        session_repository = PostgreSQLSessionRepository(isolated_database)
        job_repository = PostgreSQLSessionPostProcessingJobRepository(isolated_database)
        utterance_repository = PostgreSQLUtteranceRepository(isolated_database)
        event_repository = PostgreSQLMeetingEventRepository(isolated_database)
        session_service = SessionService(session_repository)
        artifact_store = LocalArtifactStore(tmp_path)

        session = session_service.create_session_draft(
            title="provisional transcript 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        session = session_service.start_session(session.id)
        session = session_service.end_session(session.id)

        recording_artifact = artifact_store.build_recording_artifact(
            session_id=session.id,
            input_source="system_audio",
        )
        recording_artifact.file_path.parent.mkdir(parents=True, exist_ok=True)
        recording_artifact.file_path.write_bytes(b"RIFF0000WAVEfmt ")

        provisional_snapshots: list[list[tuple[int, str]]] = []

        def inspect_progress(_: int) -> None:
            provisional_snapshots.append(
                [
                    (item.seq_num, item.transcript_source)
                    for item in utterance_repository.list_by_session(session.id)
                ]
            )

        service = SessionPostProcessingJobService(
            repository=job_repository,
            session_repository=session_repository,
            utterance_repository=utterance_repository,
            event_repository=event_repository,
            audio_postprocessing_service=_InspectingAudioPostprocessingService(inspect_progress),
            analyzer=_StubAnalyzer(),
            note_correction_job_service=_RecordingNoteCorrectionJobService(),
            artifact_store=artifact_store,
        )

        job = service.enqueue_for_session(
            session_id=session.id,
            requested_by_user_id=None,
            dispatch=False,
        )
        processed_job = service.process_job(job.id)
        finalized_utterances = utterance_repository.list_by_session(session.id)

        assert processed_job.status == "completed"
        assert provisional_snapshots == [
            [(1, "post_processing_draft")],
            [(1, "post_processing_draft"), (2, "post_processing_draft")],
        ]
        assert [item.transcript_source for item in finalized_utterances] == [
            "post_processed",
            "post_processed",
        ]
