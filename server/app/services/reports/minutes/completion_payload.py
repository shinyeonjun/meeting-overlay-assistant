"""회의록 LLM 응답을 JSON payload로 완성하는 재시도 루프."""

from __future__ import annotations

import json
import logging
import time

from server.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)
from server.app.services.reports.minutes.json_response import load_json_response
from server.app.services.reports.minutes.payload_merge import (
    find_payload_quality_issue,
    repair_payload_sections_from_supporting_fields,
)
from server.app.services.reports.minutes.prompting import (
    MEETING_MINUTES_SYSTEM_PROMPT,
    build_json_retry_prompt,
    build_quality_retry_prompt,
)
from server.app.services.reports.minutes.response_schema import RESPONSE_SCHEMA


def complete_minutes_json_payload(
    *,
    completion_client: LLMCompletionClient,
    config,
    logger: logging.Logger,
    session_id: str,
    prompt: str,
    stage: str,
    transcript_segments: int,
    validate_quality: bool = True,
) -> dict[str, object] | None:
    started_at = time.perf_counter()
    logger.info(
        "회의록 AI 분석 시작: session_id=%s model=%s stage=%s prompt_chars=%s transcript_segments=%s",
        session_id,
        config.model,
        stage,
        len(prompt),
        transcript_segments,
    )
    max_attempts = max(config.max_json_retries, 0) + 1
    last_parse_error: Exception | None = None
    retry_prompt: str | None = None
    for attempt in range(1, max_attempts + 1):
        response_text = ""
        current_prompt = retry_prompt or prompt
        try:
            payload, response_text = _complete_payload_attempt(
                completion_client=completion_client,
                config=config,
                prompt=current_prompt,
            )
            quality_issue = _find_quality_issue(
                payload,
                transcript_segments=transcript_segments,
                validate_quality=validate_quality,
            )
            if quality_issue is not None:
                retry_payload = _handle_quality_issue(
                    config=config,
                    logger=logger,
                    payload=payload,
                    quality_issue=quality_issue,
                    session_id=session_id,
                    stage=stage,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    transcript_segments=transcript_segments,
                )
                if retry_payload is _RETRY:
                    retry_prompt = build_quality_retry_prompt(prompt, quality_issue)
                    continue
                return retry_payload

            _log_completion_success(
                config=config,
                logger=logger,
                session_id=session_id,
                stage=stage,
                started_at=started_at,
                response_text=response_text,
                attempt=attempt,
                max_attempts=max_attempts,
            )
            return payload
        except (json.JSONDecodeError, ValueError) as exc:
            last_parse_error = exc
            if attempt >= max_attempts:
                break
            _log_json_retry(
                config=config,
                logger=logger,
                session_id=session_id,
                stage=stage,
                response_text=response_text,
                attempt=attempt,
                max_attempts=max_attempts,
                error=exc,
            )
            retry_prompt = build_json_retry_prompt(prompt)
        except Exception:
            _log_unexpected_completion_error(
                config=config,
                logger=logger,
                session_id=session_id,
                stage=stage,
                prompt=prompt,
                started_at=started_at,
            )
            return None

    if last_parse_error is not None:
        _log_json_final_failure(
            config=config,
            logger=logger,
            session_id=session_id,
            stage=stage,
            prompt=prompt,
            started_at=started_at,
            max_attempts=max_attempts,
            error=last_parse_error,
        )
    return None


_RETRY = object()


def _complete_payload_attempt(
    *,
    completion_client: LLMCompletionClient,
    config,
    prompt: str,
) -> tuple[dict[str, object], str]:
    response_text = completion_client.complete(
        prompt,
        system_prompt=MEETING_MINUTES_SYSTEM_PROMPT,
        response_schema=_response_schema(config),
        keep_alive=config.keep_alive,
    )
    return load_json_response(response_text), response_text


def _response_schema(config):
    return RESPONSE_SCHEMA if config.use_response_schema else None


def _find_quality_issue(
    payload: dict[str, object],
    *,
    transcript_segments: int,
    validate_quality: bool,
) -> str | None:
    if not validate_quality:
        return None
    return find_payload_quality_issue(
        payload,
        transcript_segments=transcript_segments,
    )


def _handle_quality_issue(
    *,
    config,
    logger: logging.Logger,
    payload: dict[str, object],
    quality_issue: str,
    session_id: str,
    stage: str,
    attempt: int,
    max_attempts: int,
    transcript_segments: int,
) -> dict[str, object] | None | object:
    if attempt < max_attempts:
        logger.warning(
            "회의록 AI 품질 검증 실패 후 재시도: session_id=%s model=%s stage=%s attempt=%s/%s issue=%s",
            session_id,
            config.model,
            stage,
            attempt,
            max_attempts,
            quality_issue,
        )
        return _RETRY

    return _repair_payload_after_quality_failure(
        config=config,
        logger=logger,
        payload=payload,
        quality_issue=quality_issue,
        session_id=session_id,
        stage=stage,
        attempt=attempt,
        max_attempts=max_attempts,
        transcript_segments=transcript_segments,
    )


def _repair_payload_after_quality_failure(
    *,
    config,
    logger: logging.Logger,
    payload: dict[str, object],
    quality_issue: str,
    session_id: str,
    stage: str,
    attempt: int,
    max_attempts: int,
    transcript_segments: int,
) -> dict[str, object] | None:
    repaired_payload = repair_payload_sections_from_supporting_fields(payload)
    if (
        find_payload_quality_issue(
            repaired_payload,
            transcript_segments=transcript_segments,
        )
        is None
    ):
        logger.warning(
            "회의록 AI 품질 검증 최종 실패 대신 회의내용 보정: session_id=%s model=%s stage=%s attempt=%s/%s issue=%s",
            session_id,
            config.model,
            stage,
            attempt,
            max_attempts,
            quality_issue,
        )
        return repaired_payload

    logger.error(
        "회의록 AI 품질 검증 최종 실패: session_id=%s model=%s stage=%s attempt=%s/%s issue=%s",
        session_id,
        config.model,
        stage,
        attempt,
        max_attempts,
        quality_issue,
    )
    return None


def _log_completion_success(
    *,
    config,
    logger: logging.Logger,
    session_id: str,
    stage: str,
    started_at: float,
    response_text: str,
    attempt: int,
    max_attempts: int,
) -> None:
    logger.info(
        "회의록 AI 분석 완료: session_id=%s model=%s stage=%s elapsed=%.2fs response_chars=%s attempt=%s/%s",
        session_id,
        config.model,
        stage,
        time.perf_counter() - started_at,
        len(response_text),
        attempt,
        max_attempts,
    )


def _log_json_retry(
    *,
    config,
    logger: logging.Logger,
    session_id: str,
    stage: str,
    response_text: str,
    attempt: int,
    max_attempts: int,
    error: Exception,
) -> None:
    logger.warning(
        "회의록 AI JSON 파싱 실패 후 재시도: session_id=%s model=%s stage=%s response_chars=%s attempt=%s/%s error=%s",
        session_id,
        config.model,
        stage,
        len(response_text),
        attempt,
        max_attempts,
        error,
    )


def _log_json_final_failure(
    *,
    config,
    logger: logging.Logger,
    session_id: str,
    stage: str,
    prompt: str,
    started_at: float,
    max_attempts: int,
    error: Exception,
) -> None:
    logger.error(
        "회의록 AI JSON 파싱 최종 실패: session_id=%s model=%s stage=%s prompt_chars=%s elapsed=%.2fs attempts=%s",
        session_id,
        config.model,
        stage,
        len(prompt),
        time.perf_counter() - started_at,
        max_attempts,
        exc_info=error,
    )


def _log_unexpected_completion_error(
    *,
    config,
    logger: logging.Logger,
    session_id: str,
    stage: str,
    prompt: str,
    started_at: float,
) -> None:
    logger.exception(
        "회의록 AI 분석 실패: session_id=%s model=%s stage=%s prompt_chars=%s elapsed=%.2fs",
        session_id,
        config.model,
        stage,
        len(prompt),
        time.perf_counter() - started_at,
    )
