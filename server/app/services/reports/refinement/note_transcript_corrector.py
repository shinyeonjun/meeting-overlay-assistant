"""노트용 transcript 보수적 후보정기."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from server.app.domain.models.utterance import Utterance
from server.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)
from server.app.services.reports.refinement.transcript_correction_store import (
    TranscriptCorrectionDocument,
    TranscriptCorrectionItem,
)


logger = logging.getLogger(__name__)


_CORRECTION_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "corrected_text": {"type": "string"},
        "changed": {"type": "boolean"},
        "risk_flags": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["corrected_text", "changed", "risk_flags"],
    "additionalProperties": False,
}

_DIGIT_PATTERN = re.compile(r"\d+")
_HIGH_RISK_TOKEN_PATTERN = re.compile(
    r"(\d+[./:-]\d+|\d+원|\d+만원|v\d+(?:\.\d+)*|버전\s*\d+(?:\.\d+)*)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class NoteTranscriptCorrectionConfig:
    """노트 transcript 보정 설정."""

    model: str
    max_window: int = 3


class NoteTranscriptCorrector:
    """Gemma 같은 completion model로 transcript를 보수적으로 교정한다."""

    def __init__(
        self,
        completion_client: LLMCompletionClient,
        *,
        config: NoteTranscriptCorrectionConfig,
    ) -> None:
        self._completion_client = completion_client
        self._config = config

    def correct(
        self,
        *,
        session_id: str,
        source_version: int,
        utterances: list[Utterance],
    ) -> TranscriptCorrectionDocument:
        """발화 목록을 받아 교정 결과 문서를 만든다."""

        items: list[TranscriptCorrectionItem] = []
        for index, utterance in enumerate(utterances):
            raw_text = utterance.text.strip()
            if not raw_text:
                continue

            try:
                response = self._request_correction(
                    utterances=utterances,
                    target_index=index,
                )
            except Exception as exc:
                logger.warning(
                    "노트 transcript 후보정 개별 발화 실패: utterance_id=%s speaker=%s error=%s",
                    utterance.id,
                    utterance.speaker_label or "speaker-unknown",
                    exc,
                )
                response = _CorrectionResponse(
                    corrected_text=raw_text,
                    risk_flags=["request_failed"],
                )
            corrected_text = self._sanitize_correction(
                raw_text=raw_text,
                corrected_text=response.corrected_text,
            )
            changed = corrected_text != raw_text
            items.append(
                TranscriptCorrectionItem(
                    utterance_id=utterance.id,
                    raw_text=raw_text,
                    corrected_text=corrected_text,
                    changed=changed,
                    risk_flags=response.risk_flags,
                )
            )

        return TranscriptCorrectionDocument(
            session_id=session_id,
            source_version=source_version,
            model=self._config.model,
            items=items,
        )

    def _request_correction(
        self,
        *,
        utterances: list[Utterance],
        target_index: int,
    ) -> "_CorrectionResponse":
        prompt = self._build_prompt(
            utterances=utterances,
            target_index=target_index,
        )
        response_text = self._completion_client.complete(
            prompt,
            system_prompt=_SYSTEM_PROMPT,
            response_schema=_CORRECTION_RESPONSE_SCHEMA,
            keep_alive="10m",
        )
        try:
            payload = json.loads(response_text)
        except (TypeError, ValueError):
            return _CorrectionResponse(
                corrected_text=utterances[target_index].text.strip(),
                risk_flags=["invalid_json"],
            )

        corrected_text = str(payload.get("corrected_text") or "").strip()
        if not corrected_text:
            corrected_text = utterances[target_index].text.strip()
        risk_flags = [
            str(flag).strip()
            for flag in (payload.get("risk_flags") or [])
            if str(flag).strip()
        ]
        return _CorrectionResponse(
            corrected_text=corrected_text,
            risk_flags=risk_flags,
        )

    def _build_prompt(
        self,
        *,
        utterances: list[Utterance],
        target_index: int,
    ) -> str:
        half_window = max((self._config.max_window - 1) // 2, 0)
        start_index = max(target_index - half_window, 0)
        end_index = min(target_index + half_window + 1, len(utterances))

        lines: list[str] = []
        for index in range(start_index, end_index):
            utterance = utterances[index]
            marker = "TARGET" if index == target_index else "CONTEXT"
            speaker = utterance.speaker_label or "speaker-unknown"
            lines.append(
                f"[{marker}] {speaker} {utterance.start_ms}-{utterance.end_ms}: {utterance.text.strip()}"
            )

        target = utterances[target_index]
        return "\n".join(
            [
                "아래는 한국어 회의 transcript 일부입니다.",
                "TARGET 발화만 보수적으로 교정하세요.",
                "CONTEXT는 이해를 위한 문맥이며 수정 대상이 아닙니다.",
                "",
                *lines,
                "",
                f"TARGET 원문: {target.text.strip()}",
            ]
        )

    @staticmethod
    def _sanitize_correction(*, raw_text: str, corrected_text: str) -> str:
        normalized = corrected_text.strip()
        if not normalized:
            return raw_text
        if _HIGH_RISK_TOKEN_PATTERN.search(raw_text):
            if _normalize_digits(raw_text) != _normalize_digits(normalized):
                return raw_text
        if len(normalized) > max(len(raw_text) * 3, len(raw_text) + 30):
            return raw_text
        return normalized


@dataclass(frozen=True)
class _CorrectionResponse:
    corrected_text: str
    risk_flags: list[str]


def _normalize_digits(text: str) -> tuple[str, ...]:
    return tuple(_DIGIT_PATTERN.findall(text))


_SYSTEM_PROMPT = """
너는 한국어 회의 transcript 보정기다.

규칙:
- 의미를 바꾸지 마라.
- 들리지 않은 내용을 추측해서 추가하지 마라.
- TARGET 발화만 수정하고 CONTEXT는 참고만 해라.
- 숫자, 날짜, 금액, 버전, 사람 이름, 회사명은 확신이 없으면 원문을 유지해라.
- 목표는 띄어쓰기, 문장부호, 영문 제품명 표기 통일, 명백한 오인식만 보수적으로 고치는 것이다.
- 응답은 반드시 JSON 하나만 반환해라.
""".strip()
