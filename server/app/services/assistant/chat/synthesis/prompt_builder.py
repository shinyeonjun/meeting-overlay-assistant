"""assistant 답변 프롬프트 구성."""

from __future__ import annotations

from server.app.domain.retrieval import RetrievalSearchResult
from server.app.services.assistant.chat.models import (
    AssistantQueryPlan,
    AssistantTimeContext,
)
from server.app.services.assistant.chat.synthesis.source_metadata import (
    render_source_metadata,
)
from server.app.services.assistant.chat.synthesis.text_limits import truncate_text


def build_system_prompt() -> str:
    """근거 기반 읽기 전용 assistant 시스템 프롬프트를 만든다."""

    return (
        "너는 CAPS 업무 회의 챗봇이다. 반드시 제공된 회의 근거 안에서만 답변한다. "
        "근거에 없는 내용은 추측하지 말고 확인할 수 없다고 말한다. "
        "답변은 한국어로 작성하고, 필요한 문장 끝에 [S1] 같은 근거 번호를 붙인다. "
        "회의록 생성, 삭제, 전송, 일정 변경 같은 쓰기 작업은 수행하지 않는다."
    )


def build_user_prompt(
    *,
    plan: AssistantQueryPlan,
    sources: list[RetrievalSearchResult],
    time_context: AssistantTimeContext,
) -> str:
    """검색 근거와 질문 계획을 답변 LLM 프롬프트로 렌더링한다."""

    lines = [
        "사용자 질문:",
        plan.query,
        "",
        "RAG 검색 질의:",
        plan.search_query,
        "",
        "현재 시간 문맥:",
        time_context.render_for_prompt(),
    ]
    if plan.answer_focus:
        lines.extend(["", "답변 초점:", plan.answer_focus])
    if plan.time_expression or plan.resolved_time_range or plan.time_scope:
        lines.extend(
            [
                "",
                "질문 시간 해석:",
                f"- 원문 시간 표현: {plan.time_expression or '-'}",
                f"- 해석된 시간 범위: {plan.resolved_time_range or '-'}",
                f"- 시간 범위 설명: {plan.time_scope or '-'}",
            ]
        )
    lines.extend(["", "검색된 회의 근거:"])
    for index, source in enumerate(sources, start=1):
        heading = source.chunk_heading or "제목 없음"
        text = truncate_text(source.chunk_text)
        metadata = render_source_metadata(source)
        lines.extend(
            [
                f"[S{index}] {source.document_title} / {heading}",
                f"메타: {metadata}",
                text,
                "",
            ]
        )
    lines.extend(
        [
            "답변 지침:",
            "- 핵심 답변을 먼저 쓴다.",
            "- 필요한 경우 짧은 bullet로 정리한다.",
            "- 각 근거는 [S1], [S2]처럼 표시한다.",
            "- source_type=session 근거는 회의 제목/날짜/상태 같은 세션 목록 정보다.",
            "- 사용자가 특정 날짜의 회의 목록을 물으면 결정 사항이 아니라 해당 날짜의 회의 제목과 시간을 답한다.",
            "- 근거가 부족하면 부족하다고 말한다.",
        ]
    )
    return "\n".join(lines)
