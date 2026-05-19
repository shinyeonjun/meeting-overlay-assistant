"""워크스페이스 요약 LLM JSON completion helper."""

from __future__ import annotations

import logging
import time

from server.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)
from server.app.services.analysis.llm.json_response import load_json_object_response


def complete_workspace_summary_json_payload(
    *,
    completion_client: LLMCompletionClient,
    logger: logging.Logger,
    prompt: str,
    system_prompt: str,
    response_schema: dict[str, object],
    failure_message: str,
    success_message: str,
    failure_args: tuple[object, ...],
    success_args: tuple[object, ...],
) -> dict[str, object] | None:
    started_at = time.perf_counter()
    try:
        response_text = completion_client.complete(
            prompt,
            system_prompt=system_prompt,
            response_schema=response_schema,
            keep_alive="30m",
        )
        payload = load_json_object_response(response_text)
    except Exception:
        elapsed_seconds = time.perf_counter() - started_at
        logger.exception(
            failure_message,
            *failure_args,
            len(prompt),
            elapsed_seconds,
        )
        return None

    elapsed_seconds = time.perf_counter() - started_at
    logger.info(
        success_message,
        *success_args,
        len(prompt),
        elapsed_seconds,
    )
    return payload
