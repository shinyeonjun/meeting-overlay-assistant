"""실시간 질문 감지 LLM 클라이언트."""

from __future__ import annotations

import json
import logging
from json import JSONDecodeError

from server.app.services.analysis.llm.factories.completion_client_factory import (
    create_llm_completion_client,
)
from server.app.services.live_questions.models import (
    LiveQuestionOperation,
    LiveQuestionRequest,
    LiveQuestionResult,
)
from server.app.services.live_questions.question_prompt_builder import (
    LIVE_QUESTION_RESPONSE_SCHEMA,
    build_question_analysis_prompt,
    build_question_analysis_system_prompt,
    build_question_analysis_warmup_prompt,
)

logger = logging.getLogger(__name__)


class LiveQuestionLLMClient:
    """OpenAI 호환 LLM을 사용해 안정화된 발화 window에서 질문만 감지한다."""

    def __init__(
        self,
        *,
        backend_name: str,
        model: str,
        base_url: str,
        api_key: str | None,
        timeout_seconds: float,
        keep_alive: str | None = None,
    ) -> None:
        self._keep_alive = keep_alive
        self._completion_client = create_llm_completion_client(
            backend_name=backend_name,
            model=model,
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )

    def analyze(self, request: LiveQuestionRequest) -> LiveQuestionResult:
        """질문 감지 요청을 처리한다."""

        prompt = build_question_analysis_prompt(request)
        raw = self._completion_client.complete(
            prompt,
            system_prompt=build_question_analysis_system_prompt(),
            response_schema=LIVE_QUESTION_RESPONSE_SCHEMA,
            keep_alive=self._keep_alive,
        ).strip()
        if not raw:
            return LiveQuestionResult(
                session_id=request.session_id,
                window_id=request.window_id,
                operations=(),
            )

        try:
            payload = _normalize_payload(_parse_json_payload(raw))
        except JSONDecodeError:
            logger.warning("실시간 질문 응답 JSON 파싱 실패, 빈 결과로 처리합니다: %s", raw)
            return LiveQuestionResult(
                session_id=request.session_id,
                window_id=request.window_id,
                operations=(),
            )

        operations = tuple(
            LiveQuestionOperation.from_payload(item)
            for item in (payload.get("operations") or [])
            if isinstance(item, dict)
        )
        return LiveQuestionResult(
            session_id=request.session_id,
            window_id=request.window_id,
            operations=_normalize_operations(request, operations),
        )

    def warm_up(self) -> None:
        """질문 감지 모델을 미리 깨워 첫 요청 지연을 줄인다."""

        self._completion_client.complete(
            build_question_analysis_warmup_prompt(),
            system_prompt=build_question_analysis_system_prompt(),
            response_schema=LIVE_QUESTION_RESPONSE_SCHEMA,
            keep_alive=self._keep_alive,
        )


def _parse_json_payload(raw: str) -> dict[str, object]:
    """응답 문자열에서 JSON 객체를 추출한다."""

    try:
        return json.loads(raw)
    except JSONDecodeError:
        start = raw.find("{")
        if start >= 0:
            candidate = raw[start:]
            repaired = _repair_json_brackets(candidate)
            return json.loads(repaired)
        raise


def _normalize_payload(payload: dict[str, object]) -> dict[str, object]:
    """모델 응답 wrapper를 걷어내고 operations 최상위 객체로 정규화한다."""

    nested = payload.get("response")
    if isinstance(nested, dict) and isinstance(nested.get("operations"), list):
        return nested
    return payload


def _repair_json_brackets(raw: str) -> str:
    """잘린 JSON 응답의 괄호 균형을 맞춰 파싱 가능성을 높인다."""

    trimmed = raw.strip()
    open_braces = trimmed.count("{")
    close_braces = trimmed.count("}")
    open_brackets = trimmed.count("[")
    close_brackets = trimmed.count("]")
    if close_brackets < open_brackets:
        trimmed += "]" * (open_brackets - close_brackets)
    if close_braces < open_braces:
        trimmed += "}" * (open_braces - close_braces)
    return trimmed


def _normalize_operations(
    request: LiveQuestionRequest,
    operations: tuple[LiveQuestionOperation, ...],
) -> tuple[LiveQuestionOperation, ...]:
    """MVP에서는 질문 add만 유지하고 close/answered 추적은 버린다."""

    utterance_text_by_id = {item.id: item.text.strip() for item in request.utterances}
    fallback_text = next(
        (item.text.strip() for item in reversed(request.utterances) if item.text.strip()),
        "",
    )
    normalized: list[LiveQuestionOperation] = []
    for operation in operations:
        if operation.op != "add":
            continue

        summary = (operation.summary or "").strip()
        if _is_meta_summary(summary):
            evidence_id = (
                operation.evidence_utterance_ids[0]
                if operation.evidence_utterance_ids
                else None
            )
            summary = utterance_text_by_id.get(evidence_id or "", "") or fallback_text
        normalized.append(
            LiveQuestionOperation(
                op="add",
                summary=summary or None,
                confidence=operation.confidence,
                evidence_utterance_ids=operation.evidence_utterance_ids,
                target_question_id=None,
                speaker_label=operation.speaker_label,
                reason=operation.reason,
            )
        )
    return tuple(normalized)


def _is_meta_summary(summary: str) -> bool:
    normalized = summary.strip().lower()
    if not normalized:
        return True
    meta_tokens = (
        "새 질문",
        "질문 여부",
        "질문이 불명확",
        "질문 아님",
        "불명확",
        "question",
    )
    return any(token in normalized for token in meta_tokens)
