"""회의록 생성에 사용할 RAG 참고 맥락 조회 helper."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_ID
from server.app.domain.retrieval import RetrievalSearchResult
from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)
from server.app.services.reports.composition.report_session_context import (
    ReportSessionContext,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MeetingReferenceContextConfig:
    """회의록 생성 참고 맥락 조회 설정."""

    enabled: bool = True
    limit: int = 6
    query_max_chars: int = 1200
    context_max_chars: int = 2400


class MeetingReferenceContextService:
    """기존 노트 전문 임베딩에서 회의록 생성용 참고 맥락을 가져온다."""

    def __init__(
        self,
        *,
        retrieval_query_service,
        config: MeetingReferenceContextConfig,
    ) -> None:
        self._retrieval_query_service = retrieval_query_service
        self._config = config

    def retrieve_reference_context(
        self,
        *,
        session_id: str,
        session_context: ReportSessionContext | None,
        speaker_transcript: list[SpeakerTranscriptSegment],
        workspace_id: str = DEFAULT_WORKSPACE_ID,
    ) -> list[dict[str, object]]:
        """현재 회의와 다른 노트 청크만 회의록 생성 참고 맥락으로 반환한다."""

        if not self._config.enabled or self._retrieval_query_service is None:
            return []

        query = _build_reference_query(
            session_context=session_context,
            speaker_transcript=speaker_transcript,
            max_chars=self._config.query_max_chars,
        )
        if not query:
            return []

        try:
            results = self._retrieval_query_service.search(
                workspace_id=workspace_id,
                query=query,
                source_types=("note",),
                limit=max(self._config.limit * 2, self._config.limit),
            )
        except Exception:
            logger.exception(
                "회의록 참고 맥락 조회 실패: session_id=%s",
                session_id,
            )
            return []

        return _format_reference_context(
            results,
            current_session_id=session_id,
            limit=self._config.limit,
            max_chars=self._config.context_max_chars,
        )


def _build_reference_query(
    *,
    session_context: ReportSessionContext | None,
    speaker_transcript: list[SpeakerTranscriptSegment],
    max_chars: int,
) -> str:
    parts: list[str] = []
    if session_context is not None:
        if session_context.title:
            parts.append(str(session_context.title))
        if session_context.participants:
            parts.append(" ".join(str(value) for value in session_context.participants))

    for segment in speaker_transcript[:24]:
        text = segment.text.strip()
        if text:
            parts.append(text)
        if len(" ".join(parts)) >= max_chars:
            break

    return " ".join(parts).strip()[:max(max_chars, 0)]


def _format_reference_context(
    results: list[RetrievalSearchResult],
    *,
    current_session_id: str,
    limit: int,
    max_chars: int,
) -> list[dict[str, object]]:
    formatted: list[dict[str, object]] = []
    used_chars = 0
    seen: set[str] = set()

    for result in results:
        if result.session_id == current_session_id:
            continue
        chunk_text = result.chunk_text.strip()
        if not chunk_text:
            continue
        dedupe_key = result.chunk_id or f"{result.document_id}:{result.chunk_heading}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        remaining_chars = max_chars - used_chars
        if remaining_chars <= 0:
            break
        text = chunk_text[:remaining_chars]
        used_chars += len(text)

        formatted.append(
            {
                "source_type": result.source_type,
                "title": result.document_title,
                "heading": result.chunk_heading,
                "session_id": result.session_id,
                "text": text,
            }
        )
        if len(formatted) >= limit:
            break

    return formatted


__all__ = [
    "MeetingReferenceContextConfig",
    "MeetingReferenceContextService",
]
