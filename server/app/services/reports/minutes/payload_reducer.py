"""분할 병합된 회의록 payload를 최종 회의록 payload로 재정리한다."""

from __future__ import annotations

import json
import logging
import time

from server.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)
from server.app.services.reports.minutes.json_response import load_json_response
from server.app.services.reports.minutes.response_schema import RESPONSE_SCHEMA


FINAL_REDUCE_SYSTEM_PROMPT = """
너는 분할 분석으로 만들어진 회의록 후보를 최종 회의록 payload로 정리하는 편집자다.

목표:
- 입력 payload의 사실만 사용한다.
- 새 결정, 새 담당자, 새 일정, 새 아이디어를 만들지 않는다.
- 같은 논의 축이 다른 제목이나 표현으로 반복되면 하나의 sections 항목으로 병합한다.
- 실제로 다른 논의 축은 보존한다. sections 개수는 고정하지 않는다.
- 브레인스토밍 회의에서는 결정사항을 억지로 만들지 말고, 제안/검토/미확정 쟁점을 회의내용과 special_notes에 정리한다.
- 결정형 회의에서는 명시적 합의만 decisions에 둔다.
- 농담, 감탄, 말장난은 제거하되, 그 안에 포함된 실제 제안은 공식 문서체로 정제한다.
- 같은 내용을 sections, decisions, special_notes, follow_up에 반복하지 않는다.

출력:
- 반드시 JSON object 하나만 반환한다.
- schema는 입력과 같은 agenda, overview, sections, decisions, special_notes, follow_up 구조를 따른다.
- text에는 번호, 글머리표, Markdown, HTML을 넣지 않는다.
- important_phrases에는 text에 실제 포함된 짧은 구절만 넣는다.
""".strip()


def reduce_minutes_payload(
    *,
    completion_client: LLMCompletionClient,
    config,
    logger: logging.Logger,
    session_id: str,
    payload: dict[str, object],
) -> dict[str, object]:
    """Gemma final reduce로 유사 주제를 병합하고 최종 payload를 다듬는다."""

    prompt = _build_reduce_prompt(payload)
    started_at = time.perf_counter()
    logger.info(
        "회의록 AI 최종 reduce 시작: session_id=%s model=%s sections=%s prompt_chars=%s",
        session_id,
        config.model,
        _count_sections(payload),
        len(prompt),
    )
    try:
        response_text = completion_client.complete(
            prompt,
            system_prompt=FINAL_REDUCE_SYSTEM_PROMPT,
            response_schema=(
                RESPONSE_SCHEMA if getattr(config, "use_response_schema", True) else None
            ),
            keep_alive=config.keep_alive,
        )
        reduced_payload = load_json_response(response_text)
    except Exception:
        logger.exception(
            "회의록 AI 최종 reduce 실패: session_id=%s model=%s elapsed=%.2fs",
            session_id,
            config.model,
            time.perf_counter() - started_at,
        )
        return payload

    logger.info(
        "회의록 AI 최종 reduce 완료: session_id=%s model=%s elapsed=%.2fs sections=%s->%s",
        session_id,
        config.model,
        time.perf_counter() - started_at,
        _count_sections(payload),
        _count_sections(reduced_payload),
    )
    return reduced_payload


def _build_reduce_prompt(payload: dict[str, object]) -> str:
    return json.dumps(
        {
            "instruction": (
                "다음 merged_payload를 최종 회의록 payload로 편집한다. "
                "소주제 개수는 고정하지 말고, 의미상 같은 논의 축만 병합한다."
            ),
            "merged_payload": payload,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _count_sections(payload: dict[str, object]) -> int:
    sections = payload.get("sections")
    return len(sections) if isinstance(sections, list) else 0
