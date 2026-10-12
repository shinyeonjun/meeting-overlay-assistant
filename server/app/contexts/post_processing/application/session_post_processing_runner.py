"""session 후처리 job 하나를 실행하고 성공, 실패, claim 상실 결과를 기록한다."""

from __future__ import annotations

import logging
from pathlib import Path

from server.app.contexts.live_capture import resolve_recording_reference
from server.app.domain.models.session_post_processing_job import SessionPostProcessingJob
from server.app.domain.models.utterance import POST_PROCESSING_DRAFT_SOURCE, Utterance
from server.app.workers.job_claim_fence import (
    StaleJobClaimError,
    resolve_processing_job,
)


logger = logging.getLogger(__name__)


class SessionPostProcessingRunMixin:
    """`SessionPostProcessingJobService`가 상속하는 job 실행 파이프라인이다.

    인스턴스 속성, 의존성 getter, claim 펜싱과 canonical 상태 헬퍼는 서비스 클래스가 제공한다.
    """

    def process_job(
        self,
        job_id: str,
        *,
        expected_worker_id: str | None = None,
    ) -> SessionPostProcessingJob:
        """세션 후처리 job 하나를 처리한다."""

        processing_job = resolve_processing_job(
            self._repository,
            job_id=job_id,
            expected_worker_id=expected_worker_id,
            label="세션 후처리 job",
        )
        if processing_job.status == "completed":
            return processing_job

        session = self._session_repository.get_by_id(processing_job.session_id)
        if session is None:
            failed_job = processing_job.mark_failed(f"존재하지 않는 세션입니다: {processing_job.session_id}")
            return self._repository.update(failed_job)

        self._ensure_processing_dependencies()

        started_session = self._session_repository.save(
            session.mark_post_processing_started(
                recording_artifact_id=processing_job.recording_artifact_id,
            )
        )
        previous_canonical_state = self._snapshot_canonical_state(started_session.id)
        canonical_replaced = False
        # 이 worker가 쓰기 권한을 가진 worker ID. 인프로세스 처리는 None이라 펜싱하지 않는다.
        fence_worker_id = expected_worker_id or processing_job.claimed_by_worker_id

        try:
            recording_path = resolve_recording_reference(
                artifact_id=processing_job.recording_artifact_id,
                fallback_path=processing_job.recording_path,
                artifact_store=self._artifact_store,
            )
            if recording_path is None or not Path(recording_path).exists():
                raise ValueError("후처리할 원본 녹음 파일을 찾을 수 없습니다.")

            # 원본 transcript는 교체 직전까지 DB에 그대로 둔다. 진행 중 초안은
            # 원본 뒤 seq_num으로 별도 source에 쌓고, 완료 시점에 한 트랜잭션으로 교체한다.
            # 그래야 worker가 중간에 죽어도 원본이 남는다. 이전 시도가 남긴 초안은 먼저 지운다.
            self._discard_provisional_transcript(started_session.id)
            provisional_sequence = self._utterance_repository.next_sequence(started_session.id) - 1

            def persist_provisional_segment(segment) -> None:
                nonlocal provisional_sequence
                text = segment.text.strip()
                if not text:
                    return
                provisional_sequence += 1
                self._utterance_repository.save(
                    Utterance.create(
                        session_id=started_session.id,
                        seq_num=provisional_sequence,
                        start_ms=segment.start_ms,
                        end_ms=segment.end_ms,
                        text=text,
                        confidence=segment.confidence,
                        input_source=started_session.primary_input_source,
                        stt_backend="post_processed",
                        latency_ms=None,
                        speaker_label=segment.speaker_label,
                        transcript_source=POST_PROCESSING_DRAFT_SOURCE,
                        processing_job_id=processing_job.id,
                    )
                )

            speaker_transcript = self._get_audio_postprocessing_service().build_speaker_transcript(
                recording_path,
                on_segment=persist_provisional_segment,
            )
            canonical_utterances = self._build_canonical_utterances(
                session_id=started_session.id,
                input_source=started_session.primary_input_source,
                processing_job_id=processing_job.id,
                speaker_transcript=speaker_transcript,
            )
            canonical_events = self._build_canonical_events(
                utterances=canonical_utterances,
                processing_job_id=processing_job.id,
            )

            # 전체 전사가 끝나면 provisional rows를 final canonical rows로 교체한다.
            # lease가 넘어갔다면 교체 전에 멈춰서 다른 worker의 결과를 덮지 않는다.
            self._ensure_claim_held(processing_job, fence_worker_id)
            self._replace_canonical_state(
                session_id=started_session.id,
                utterances=canonical_utterances,
                events=canonical_events,
            )
            canonical_replaced = True

            completed_session = self._session_repository.save(
                started_session.mark_post_processing_completed(
                    recording_artifact_id=processing_job.recording_artifact_id,
                )
            )
            completed_job = self._write_terminal_job(
                processing_job.mark_completed(),
                fence_worker_id,
            )

            note_correction_job_service = self._get_note_correction_job_service()
            if note_correction_job_service is not None:
                note_correction_job_service.enqueue_for_session(
                    session_id=completed_session.id,
                    source_version=completed_session.canonical_transcript_version,
                    requested_by_user_id=processing_job.requested_by_user_id,
                    dispatch=True,
                )

            return completed_job
        except StaleJobClaimError:
            logger.warning(
                "세션 후처리 job claim을 잃어 결과를 쓰지 않았습니다: job_id=%s worker_id=%s",
                processing_job.id,
                fence_worker_id,
            )
            return self._repository.get_by_id(processing_job.id) or processing_job
        except Exception as error:
            logger.exception(
                "세션 후처리 job 처리 실패: session_id=%s job_id=%s worker_id=%s",
                processing_job.session_id,
                processing_job.id,
                expected_worker_id,
            )
            if not self._is_claim_held(processing_job.id, fence_worker_id):
                # 다른 worker가 이미 이어받았다면 canonical 상태와 job을 건드리지 않는다.
                logger.warning("claim이 넘어가 실패 복구를 건너뜁니다: job_id=%s", processing_job.id)
                return self._repository.get_by_id(processing_job.id) or processing_job
            if canonical_replaced:
                self._restore_canonical_state(
                    session_id=processing_job.session_id,
                    snapshot=previous_canonical_state,
                )
            else:
                self._discard_provisional_transcript(processing_job.session_id)
            latest_session = self._session_repository.get_by_id(processing_job.session_id)
            if latest_session is not None:
                self._session_repository.save(
                    latest_session.mark_post_processing_failed(
                        str(error),
                        recording_artifact_id=processing_job.recording_artifact_id,
                    )
                )
            failed_job = processing_job.mark_failed(str(error))
            try:
                return self._write_terminal_job(failed_job, fence_worker_id)
            except StaleJobClaimError:
                return self._repository.get_by_id(processing_job.id) or processing_job
