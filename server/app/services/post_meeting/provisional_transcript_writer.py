"""세션 후처리 중 진행 상황으로 보여줄 임시 전사를 저장한다."""

from __future__ import annotations

from server.app.domain.models.utterance import Utterance
from server.app.repositories.contracts.utterance_repository import UtteranceRepository
from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)


class ProvisionalTranscriptWriter:
    """후처리 draft 전사를 순번대로 저장한다."""

    def __init__(
        self,
        *,
        utterance_repository: UtteranceRepository,
        session_id: str,
        input_source: str,
        processing_job_id: str,
    ) -> None:
        self._utterance_repository = utterance_repository
        self._session_id = session_id
        self._input_source = input_source
        self._processing_job_id = processing_job_id
        self._sequence = 0

    @property
    def sequence(self) -> int:
        """현재까지 저장한 draft 전사 수를 반환한다."""

        return self._sequence

    def persist(self, segment: SpeakerTranscriptSegment) -> None:
        """빈 텍스트가 아닌 segment를 post-processing draft 전사로 저장한다."""

        text = segment.text.strip()
        if not text:
            return
        self._sequence += 1
        self._utterance_repository.save(
            Utterance.create(
                session_id=self._session_id,
                seq_num=self._sequence,
                start_ms=segment.start_ms,
                end_ms=segment.end_ms,
                text=text,
                confidence=segment.confidence,
                input_source=self._input_source,
                stt_backend="post_processed",
                latency_ms=None,
                speaker_label=segment.speaker_label,
                transcript_source="post_processing_draft",
                processing_job_id=self._processing_job_id,
            )
        )
