"""발화 엔티티."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from uuid import uuid4

# 세션 후처리가 진행 중일 때 원본 transcript 옆에 임시로 쌓는 발화의 source.
# 후처리가 끝나면 canonical 발화로 한 번에 교체되고, 실패하면 버려진다.
POST_PROCESSING_DRAFT_SOURCE = "post_processing_draft"


@dataclass(frozen=True)
class Utterance:
    """발화 텍스트 엔티티."""

    id: str
    session_id: str
    seq_num: int
    start_ms: int
    end_ms: int
    text: str
    confidence: float
    input_source: str | None = None
    stt_backend: str | None = None
    latency_ms: int | None = None
    speaker_label: str | None = None
    transcript_source: str = "live"
    processing_job_id: str | None = None

    @classmethod
    def create(
        cls,
        session_id: str,
        seq_num: int,
        start_ms: int,
        end_ms: int,
        text: str,
        confidence: float,
        input_source: str | None = None,
        stt_backend: str | None = None,
        latency_ms: int | None = None,
        speaker_label: str | None = None,
        transcript_source: str = "live",
        processing_job_id: str | None = None,
    ) -> "Utterance":
        """새 발화를 생성한다. 시간 순서와 순번이 잘못되면 거부한다."""
        if seq_num < 1:
            raise ValueError("발화 순번은 1 이상이어야 합니다.")
        if start_ms < 0 or end_ms < start_ms:
            raise ValueError(f"발화 시간 범위가 올바르지 않습니다: start_ms={start_ms} end_ms={end_ms}")
        return cls(
            id=f"utt-{uuid4().hex}",
            session_id=session_id,
            seq_num=seq_num,
            start_ms=start_ms,
            end_ms=end_ms,
            text=text,
            confidence=confidence,
            input_source=input_source,
            stt_backend=stt_backend,
            latency_ms=latency_ms,
            speaker_label=speaker_label,
            transcript_source=transcript_source,
            processing_job_id=processing_job_id,
        )

    @property
    def is_post_processing_draft(self) -> bool:
        return self.transcript_source == POST_PROCESSING_DRAFT_SOURCE


def select_visible_utterances(
    utterances: Iterable[Utterance],
    *,
    prefer_drafts: bool = False,
) -> list[Utterance]:
    """후처리 draft와 원본이 섞여 있을 때 보여줄 발화만 고른다.

    prefer_drafts가 True(후처리 진행 중 화면)이고 draft가 있으면 draft만,
    그 외에는 draft를 뺀 발화만 반환한다.
    """

    items = list(utterances)
    drafts = [item for item in items if item.is_post_processing_draft]
    if prefer_drafts and drafts:
        return drafts
    return [item for item in items if not item.is_post_processing_draft]
