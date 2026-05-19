"""STT 전사를 회의록 정본 섹션으로 분석하는 서비스."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from server.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)
from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)
from server.app.services.reports.composition.report_document import ReportDocumentV1
from server.app.services.reports.composition.report_session_context import (
    ReportSessionContext,
)
from server.app.services.reports.minutes.completion_payload import (
    complete_minutes_json_payload,
)
from server.app.services.reports.minutes.document_payload_mapper import (
    build_report_document_from_minutes_payload,
)
from server.app.services.reports.minutes.payload_merge import (
    find_payload_quality_issue as _find_payload_quality_issue,
    merge_chunk_payloads as _merge_chunk_payloads,
    repair_payload_sections_from_supporting_fields as _repair_payload_sections_from_supporting_fields,
)
from server.app.services.reports.minutes.prompt_payload_builder import (
    MeetingMinutesPromptPayloadMixin,
    _chunk_segments,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MeetingMinutesAnalyzerConfig:
    """회의록 AI 분석 설정."""

    model: str
    max_transcript_chars: int = 8_000
    max_event_candidates: int = 12
    map_reduce_segment_threshold: int = 36
    max_segments_per_chunk: int = 20
    max_json_retries: int = 1
    keep_alive: str | None = "30m"
    use_response_schema: bool = True


class NoOpMeetingMinutesAnalyzer:
    """회의록 AI 분석을 비활성화한다."""

    def analyze(
        self,
        *,
        session_id: str,
        session_context: ReportSessionContext | None,
        speaker_transcript: list[SpeakerTranscriptSegment],
        events: list,
        fallback_document: ReportDocumentV1,
    ) -> ReportDocumentV1 | None:
        del session_id, session_context, speaker_transcript, events, fallback_document
        return None


class LLMMeetingMinutesAnalyzer(MeetingMinutesPromptPayloadMixin):
    """교정된 STT 전체를 LLM에 보내 공유용 회의록 섹션을 만든다."""

    def __init__(
        self,
        completion_client: LLMCompletionClient,
        *,
        config: MeetingMinutesAnalyzerConfig,
    ) -> None:
        self._completion_client = completion_client
        self._config = config

    def analyze(
        self,
        *,
        session_id: str,
        session_context: ReportSessionContext | None,
        speaker_transcript: list[SpeakerTranscriptSegment],
        events: list,
        fallback_document: ReportDocumentV1,
    ) -> ReportDocumentV1 | None:
        """LLM 분석이 성공하면 fallback 문서 위에 회의록 섹션을 덮어쓴다."""

        if not speaker_transcript:
            return None

        payload = self._analyze_payload(
            session_id=session_id,
            session_context=session_context,
            speaker_transcript=speaker_transcript,
            events=events,
        )
        if payload is None:
            return None

        return build_report_document_from_minutes_payload(
            payload,
            fallback_document=fallback_document,
        )

    def _analyze_payload(
        self,
        *,
        session_id: str,
        session_context: ReportSessionContext | None,
        speaker_transcript: list[SpeakerTranscriptSegment],
        events: list,
    ) -> dict[str, object] | None:
        if self._should_use_chunked_analysis(speaker_transcript):
            return self._analyze_payload_in_chunks(
                session_id=session_id,
                session_context=session_context,
                speaker_transcript=speaker_transcript,
                events=events,
            )

        prompt = self._build_prompt(
            session_id=session_id,
            session_context=session_context,
            speaker_transcript=speaker_transcript,
            events=events,
        )
        return self._complete_json_payload(
            session_id=session_id,
            prompt=prompt,
            stage="single",
            transcript_segments=len(speaker_transcript),
        )

    def _should_use_chunked_analysis(
        self,
        speaker_transcript: list[SpeakerTranscriptSegment],
    ) -> bool:
        threshold = max(self._config.map_reduce_segment_threshold, 1)
        max_segments = max(self._config.max_segments_per_chunk, 1)
        return len(speaker_transcript) > threshold and len(speaker_transcript) > max_segments

    def _analyze_payload_in_chunks(
        self,
        *,
        session_id: str,
        session_context: ReportSessionContext | None,
        speaker_transcript: list[SpeakerTranscriptSegment],
        events: list,
    ) -> dict[str, object] | None:
        chunks = _chunk_segments(
            speaker_transcript,
            max_segments=max(self._config.max_segments_per_chunk, 1),
        )
        logger.info(
            "회의록 AI 분할 분석 시작: session_id=%s model=%s transcript_segments=%s chunks=%s chunk_size=%s",
            session_id,
            self._config.model,
            len(speaker_transcript),
            len(chunks),
            max(self._config.max_segments_per_chunk, 1),
        )

        payloads, failed_chunks = self._complete_chunk_payloads(
            session_id=session_id,
            session_context=session_context,
            chunks=chunks,
            events=events,
        )

        if not payloads:
            logger.warning(
                "회의록 AI 분할 분석 결과 없음: session_id=%s model=%s chunks=%s",
                session_id,
                self._config.model,
                len(chunks),
            )
            return None

        if failed_chunks:
            logger.warning(
                "회의록 AI 분할 분석 일부 chunk 실패 후 부분 병합: session_id=%s model=%s success_chunks=%s failed_chunks=%s total_chunks=%s",
                session_id,
                self._config.model,
                len(payloads),
                failed_chunks,
                len(chunks),
            )

        logger.info(
            "회의록 AI 분할 분석 병합: session_id=%s model=%s success_chunks=%s total_chunks=%s",
            session_id,
            self._config.model,
            len(payloads),
            len(chunks),
        )
        return self._finalize_merged_payload(
            session_id=session_id,
            payload=_merge_chunk_payloads(payloads),
            transcript_segments=len(speaker_transcript),
        )

    def _complete_chunk_payloads(
        self,
        *,
        session_id: str,
        session_context: ReportSessionContext | None,
        chunks: list[list[SpeakerTranscriptSegment]],
        events: list,
    ) -> tuple[list[dict[str, object]], list[int]]:
        payloads: list[dict[str, object]] = []
        failed_chunks: list[int] = []
        total_chunks = len(chunks)
        for index, chunk in enumerate(chunks, start=1):
            prompt = self._build_prompt(
                session_id=session_id,
                session_context=session_context,
                speaker_transcript=chunk,
                events=events,
                analysis_scope=f"chunk {index}/{total_chunks}",
            )
            payload = self._complete_json_payload(
                session_id=session_id,
                prompt=prompt,
                stage=f"chunk {index}/{total_chunks}",
                transcript_segments=len(chunk),
                validate_quality=False,
            )
            if payload is None:
                failed_chunks.append(index)
                logger.warning(
                    "회의록 AI 분할 분석 chunk 실패: session_id=%s model=%s failed_chunk=%s/%s",
                    session_id,
                    self._config.model,
                    index,
                    total_chunks,
                )
                continue
            payloads.append(_repair_payload_sections_from_supporting_fields(payload))
        return payloads, failed_chunks

    def _finalize_merged_payload(
        self,
        *,
        session_id: str,
        payload: dict[str, object],
        transcript_segments: int,
    ) -> dict[str, object] | None:
        quality_issue = _find_payload_quality_issue(
            payload,
            transcript_segments=transcript_segments,
        )
        if quality_issue is None:
            return payload

        repaired_payload = _repair_payload_sections_from_supporting_fields(payload)
        if (
            _find_payload_quality_issue(
                repaired_payload,
                transcript_segments=transcript_segments,
            )
            is None
        ):
            logger.warning(
                "회의록 AI 분할 분석 병합 결과 회의내용 보정: session_id=%s model=%s issue=%s",
                session_id,
                self._config.model,
                quality_issue,
            )
            return repaired_payload

        logger.error(
            "회의록 AI 분할 분석 병합 결과 품질 검증 실패: session_id=%s model=%s issue=%s",
            session_id,
            self._config.model,
            quality_issue,
        )
        return None

    def _complete_json_payload(
        self,
        *,
        session_id: str,
        prompt: str,
        stage: str,
        transcript_segments: int,
        validate_quality: bool = True,
    ) -> dict[str, object] | None:
        return complete_minutes_json_payload(
            completion_client=self._completion_client,
            config=self._config,
            logger=logger,
            session_id=session_id,
            prompt=prompt,
            stage=stage,
            transcript_segments=transcript_segments,
            validate_quality=validate_quality,
        )
