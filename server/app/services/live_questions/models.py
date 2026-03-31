"""실시간 질문 감지 모델."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from uuid import uuid4


def _now_ms() -> int:
    return int(time() * 1000)


@dataclass(frozen=True, slots=True)
class LiveQuestionUtterance:
    """질문 분석에 필요한 발화 스냅샷."""

    id: str
    text: str
    speaker_label: str | None
    timestamp_ms: int | None
    confidence: float

    @classmethod
    def from_utterance(cls, utterance) -> "LiveQuestionUtterance":
        """일반 발화 모델을 질문 분석용 스냅샷으로 변환한다."""

        return cls(
            id=str(utterance.id),
            text=str(utterance.text or ""),
            speaker_label=getattr(utterance, "speaker_label", None),
            timestamp_ms=getattr(utterance, "end_ms", None),
            confidence=float(getattr(utterance, "confidence", 0.0) or 0.0),
        )

    def to_payload(self) -> dict[str, object]:
        """Redis payload 직렬화용 dict를 만든다."""

        return {
            "id": self.id,
            "text": self.text,
            "speaker_label": self.speaker_label,
            "timestamp_ms": self.timestamp_ms,
            "confidence": self.confidence,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "LiveQuestionUtterance":
        """Redis payload에서 질문 분석용 발화 스냅샷을 복원한다."""

        return cls(
            id=str(payload.get("id") or ""),
            text=str(payload.get("text") or ""),
            speaker_label=(
                str(payload["speaker_label"])
                if payload.get("speaker_label") not in {None, ""}
                else None
            ),
            timestamp_ms=(
                int(payload["timestamp_ms"])
                if payload.get("timestamp_ms") is not None
                else None
            ),
            confidence=float(payload.get("confidence") or 0.0),
        )


@dataclass(frozen=True, slots=True)
class LiveQuestionItem:
    """열려 있는 질문 요약."""

    id: str
    summary: str
    speaker_label: str | None = None
    confidence: float = 0.0

    def to_payload(self) -> dict[str, object]:
        """Redis payload 직렬화용 dict를 만든다."""

        return {
            "id": self.id,
            "summary": self.summary,
            "speaker_label": self.speaker_label,
            "confidence": self.confidence,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "LiveQuestionItem":
        """Redis payload에서 질문 요약을 복원한다."""

        return cls(
            id=str(payload.get("id") or ""),
            summary=str(payload.get("summary") or ""),
            speaker_label=(
                str(payload["speaker_label"])
                if payload.get("speaker_label") not in {None, ""}
                else None
            ),
            confidence=float(payload.get("confidence") or 0.0),
        )


@dataclass(frozen=True, slots=True)
class LiveQuestionRequest:
    """실시간 질문 분석 요청."""

    session_id: str
    window_id: str
    utterances: tuple[LiveQuestionUtterance, ...]
    open_questions: tuple[LiveQuestionItem, ...]
    created_at_ms: int = field(default_factory=_now_ms)

    @classmethod
    def create(
        cls,
        *,
        session_id: str,
        utterances: list[LiveQuestionUtterance],
        open_questions: list[LiveQuestionItem],
    ) -> "LiveQuestionRequest":
        """질문 분석 요청을 새로 만든다."""

        return cls(
            session_id=session_id,
            window_id=f"lqw-{uuid4().hex}",
            utterances=tuple(utterances),
            open_questions=tuple(open_questions),
        )

    def to_payload(self) -> dict[str, object]:
        """Redis payload 직렬화용 dict를 만든다."""

        return {
            "session_id": self.session_id,
            "window_id": self.window_id,
            "utterances": [item.to_payload() for item in self.utterances],
            "open_questions": [item.to_payload() for item in self.open_questions],
            "created_at_ms": self.created_at_ms,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "LiveQuestionRequest":
        """Redis payload에서 질문 분석 요청을 복원한다."""

        return cls(
            session_id=str(payload.get("session_id") or ""),
            window_id=str(payload.get("window_id") or ""),
            utterances=tuple(
                LiveQuestionUtterance.from_payload(item)
                for item in (payload.get("utterances") or [])
                if isinstance(item, dict)
            ),
            open_questions=tuple(
                LiveQuestionItem.from_payload(item)
                for item in (payload.get("open_questions") or [])
                if isinstance(item, dict)
            ),
            created_at_ms=int(payload.get("created_at_ms") or _now_ms()),
        )


@dataclass(frozen=True, slots=True)
class LiveQuestionOperation:
    """실시간 질문 보드에 반영할 연산."""

    op: str
    summary: str | None = None
    confidence: float = 0.0
    evidence_utterance_ids: tuple[str, ...] = ()
    target_question_id: str | None = None
    speaker_label: str | None = None
    reason: str | None = None

    def to_payload(self) -> dict[str, object]:
        """Redis payload 직렬화용 dict를 만든다."""

        return {
            "op": self.op,
            "summary": self.summary,
            "confidence": self.confidence,
            "evidence_utterance_ids": list(self.evidence_utterance_ids),
            "target_question_id": self.target_question_id,
            "speaker_label": self.speaker_label,
            "reason": self.reason,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "LiveQuestionOperation":
        """Redis payload에서 질문 연산을 복원한다."""

        return cls(
            op=str(payload.get("op") or ""),
            summary=(
                str(payload["summary"])
                if payload.get("summary") not in {None, ""}
                else None
            ),
            confidence=float(payload.get("confidence") or 0.0),
            evidence_utterance_ids=tuple(
                str(item)
                for item in (payload.get("evidence_utterance_ids") or [])
                if item not in {None, ""}
            ),
            target_question_id=(
                str(payload["target_question_id"])
                if payload.get("target_question_id") not in {None, ""}
                else None
            ),
            speaker_label=(
                str(payload["speaker_label"])
                if payload.get("speaker_label") not in {None, ""}
                else None
            ),
            reason=(
                str(payload["reason"])
                if payload.get("reason") not in {None, ""}
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class LiveQuestionResult:
    """실시간 질문 분석 결과."""

    session_id: str
    window_id: str
    operations: tuple[LiveQuestionOperation, ...]
    created_at_ms: int = field(default_factory=_now_ms)

    def to_payload(self) -> dict[str, object]:
        """Redis payload 직렬화용 dict를 만든다."""

        return {
            "session_id": self.session_id,
            "window_id": self.window_id,
            "operations": [item.to_payload() for item in self.operations],
            "created_at_ms": self.created_at_ms,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "LiveQuestionResult":
        """Redis payload에서 질문 분석 결과를 복원한다."""

        return cls(
            session_id=str(payload.get("session_id") or ""),
            window_id=str(payload.get("window_id") or ""),
            operations=tuple(
                LiveQuestionOperation.from_payload(item)
                for item in (payload.get("operations") or [])
                if isinstance(item, dict)
            ),
            created_at_ms=int(payload.get("created_at_ms") or _now_ms()),
        )
