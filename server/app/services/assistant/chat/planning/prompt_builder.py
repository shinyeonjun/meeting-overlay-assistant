"""assistant 질문 계획 프롬프트."""

from __future__ import annotations


def build_planner_system_prompt() -> str:
    """질문 planning 전용 system prompt를 만든다."""

    return (
        "너는 CAPS 회의 자료 RAG 검색 계획기다. 답변을 생성하지 말고, "
        "사용자 질문을 검색에 적합한 구조로만 바꾼다. "
        "코드 고정 규칙이나 분류표를 가정하지 말고 질문 의미와 제공된 범위만 사용한다. "
        "반드시 JSON만 반환한다."
    )


def build_planner_prompt(
    *,
    query: str,
    requested_source_types: tuple[str, ...],
    time_context_text: str,
) -> str:
    """사용자 질문을 검색 계획으로 변환하는 user prompt를 만든다."""

    requested = ", ".join(requested_source_types) if requested_source_types else "없음"
    return "\n".join(
        [
            "사용자 질문을 CAPS 지식 검색용 계획으로 변환하세요.",
            "",
            "현재 시간 문맥:",
            time_context_text,
            "",
            f"질문: {query}",
            f"요청에서 이미 지정된 검색 범위: {requested}",
            "",
            "사용 가능한 근거 소스:",
            "- sessions: 회의 제목, 날짜/시간, 상태, 입력 소스, 참여자 같은 세션 메타데이터",
            "- knowledge: 회의록, 노트 인사이트, 결정 사항, 회의 내용, 후속 작업 같은 본문 지식",
            "",
            "작성 기준:",
            "- search_query는 임베딩 검색에 유리하도록 핵심 명사, 회의명, 날짜, 결정/액션 관점을 보존한다.",
            "- 오늘, 어제, 최근, 이번 주, 지난번 같은 상대 시간 표현은 현재 시간 문맥 기준으로 해석한다.",
            "- 특정 날짜에 어떤 회의가 있었는지, 최근 회의가 무엇인지처럼 회의 목록/메타데이터 질문이면 retrieval_sources에 sessions를 포함한다.",
            "- 회의에서 무엇을 논의했는지, 결정/액션/리스크가 무엇인지처럼 내용 질문이면 retrieval_sources에 knowledge를 포함한다.",
            "- 질문이 회의 목록과 회의 내용을 모두 요구하면 sessions와 knowledge를 모두 포함한다.",
            "- 날짜가 명확하면 target_dates에 YYYY-MM-DD 형식으로 넣는다.",
            "- time_scope, time_expression, resolved_time_range는 검색/답변에 참고할 시간 문맥만 기록한다.",
            "- 검색 범위는 코드가 이미 받은 요청 범위를 따르므로 새로 분류하지 않는다.",
            "- needs_clarification은 질문만으로 검색 범위를 전혀 정할 수 없을 때만 true로 둔다.",
            "- 회의 자료에 없는 사실을 만들지 않는다.",
        ]
    )
