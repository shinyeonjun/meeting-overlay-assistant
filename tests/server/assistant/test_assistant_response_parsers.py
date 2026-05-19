"""assistant 응답 파서 테스트."""

from __future__ import annotations

from server.app.services.assistant.chat.planning.response_parser import parse_plan
from server.app.services.assistant.chat.synthesis.response_parser import normalize_answer


def test_parse_plan은_fenced_json과_trailing_comma를_허용한다() -> None:
    plan = parse_plan(
        query="4월 4일 회의 뭐였지?",
        requested_source_types=("report",),
        response_text="""
        ```json
        {
          "search_query": "2026-04-04 회의",
          "answer_focus": "해당 날짜 회의 내용",
          "retrieval_sources": ["knowledge",],
          "target_dates": ["2026-04-04",],
          "time_scope": "specific_date",
          "time_expression": "4월 4일",
          "resolved_time_range": "2026-04-04 KST",
          "needs_clarification": false,
          "clarification_question": null,
          "confidence": 0.91,
        }
        ```
        """,
    )

    assert plan.search_query == "2026-04-04 회의"
    assert plan.answer_focus == "해당 날짜 회의 내용"
    assert plan.retrieval_sources == ("knowledge",)
    assert plan.target_dates == ("2026-04-04",)
    assert plan.preferred_source_types == ("report",)
    assert plan.confidence == 0.91


def test_parse_plan은_깨진_json이면_원질문으로_fallback한다() -> None:
    plan = parse_plan(
        query="최근 회의 알려줘",
        requested_source_types=(),
        response_text="not-json",
    )

    assert plan.search_query == "최근 회의 알려줘"
    assert plan.retrieval_sources == ("knowledge",)
    assert plan.target_dates == ()


def test_normalize_answer는_fenced_json_answer를_추출한다() -> None:
    answer = normalize_answer(
        """
        ```json
        {
          "answer": "최근 회의는 7분 테스트 회의입니다.",
        }
        ```
        """
    )

    assert answer == "최근 회의는 7분 테스트 회의입니다."


def test_normalize_answer는_일반_본문을_그대로_보존한다() -> None:
    answer = normalize_answer("근거에 따르면 최근 회의는 7분 테스트 회의입니다. [S1]")

    assert answer == "근거에 따르면 최근 회의는 7분 테스트 회의입니다. [S1]"
