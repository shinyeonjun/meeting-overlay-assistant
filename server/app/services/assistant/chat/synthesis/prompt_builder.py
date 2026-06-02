"""assistant 답변 프롬프트 구성."""

from __future__ import annotations

from server.app.domain.retrieval import RetrievalSearchResult
from server.app.services.assistant.chat.history_context import render_conversation_history
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
        "너는 CAPS 회의 자료 챗봇이다. 제공된 근거 안에서만 한국어로 답한다. "
        "사용자가 물은 내용만 먼저 답하고, 묻지 않은 결정사항/액션아이템/리스크/질문 섹션을 만들지 않는다. "
        "기본 답변은 1~3문장 또는 짧은 bullet 3개 이내로 작성한다. "
        "필요한 문장 끝에만 [S1] 같은 근거 번호를 붙인다. 근거가 부족하면 부족하다고 말한다. "
        "회의 생성, 삭제, 전송, 일정 변경 같은 외부 작업은 수행하지 않는다."
    )


def build_user_prompt(
    *,
    plan: AssistantQueryPlan,
    sources: list[RetrievalSearchResult],
    time_context: AssistantTimeContext,
    conversation_history=(),
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
    history_text = render_conversation_history(conversation_history)
    if history_text:
        lines.extend(["", "최근 대화:", history_text])
    if plan.answer_focus:
        lines.extend(["", "답변 초점:", plan.answer_focus])
    lines.extend(["", "답변 모드:", _infer_answer_mode_instruction(plan)])
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
            "- 사용자가 물은 것만 답한다.",
            "- 목록/확인 질문은 제목, 날짜, 한 줄 설명만 간단히 답한다.",
            "- 결정/액션/리스크/질문은 사용자가 명시적으로 물었을 때만 별도 항목으로 나눈다.",
            "- 각 근거는 [S1], [S2]처럼 필요한 곳에만 표시한다.",
            "- 결정/액션/리스크 질문을 물으면 메타 섹션을 참고하되 해당 항목만 우선 답한다.",
            "- 원문이나 누가 말했는지를 물으면 발화 시간/화자 메타를 함께 표시한다.",
            "- source_type=session 근거는 회의 제목/날짜/상태 같은 세션 목록 정보다.",
            "- 사용자가 특정 날짜/월의 회의 목록을 물으면 결정사항이 아니라 회의 제목과 시간을 답한다.",
            "- 근거가 부족하면 부족하다고 말한다.",
        ]
    )
    return "\n".join(lines)


def _infer_answer_mode_instruction(plan: AssistantQueryPlan) -> str:
    query = plan.query.replace(" ", "")
    if "sessions" in plan.retrieval_sources and "knowledge" not in plan.retrieval_sources:
        return (
            "회의 목록/메타데이터 질문이다. 회의 제목, 일시, 필요하면 한 줄 설명만 답한다. "
            "결정사항, 액션아이템, 리스크, 질문 섹션은 만들지 않는다."
        )
    if any(term in query for term in ("결정", "합의")):
        return "결정사항만 짧게 답한다."
    if any(term in query for term in ("액션", "할일", "해야할일", "다음할일")):
        return "액션아이템만 짧게 답한다."
    if any(term in query for term in ("리스크", "위험", "우려", "문제")):
        return "리스크만 짧게 답한다."
    if any(term in query for term in ("원문", "발언", "누가말")):
        return "관련 발언 원문과 시간/화자를 우선 답한다."
    return "일반 내용 질문이다. 핵심 답변만 1~3문장으로 답한다."
