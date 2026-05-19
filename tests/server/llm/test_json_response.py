"""LLM JSON 응답 파싱 유틸 테스트."""

from __future__ import annotations

import pytest

from server.app.services.analysis.llm.json_response import (
    load_json_object_response,
    load_json_value_response,
)


def test_load_json_object_response는_markdown_fence와_설명문을_제거한다() -> None:
    payload = load_json_object_response(
        """
        응답은 다음과 같습니다.
        ```json
        {
          "agenda": "회의록 점검",
          "items": ["JSON fence 제거"]
        }
        ```
        """
    )

    assert payload == {
        "agenda": "회의록 점검",
        "items": ["JSON fence 제거"],
    }


def test_load_json_object_response는_trailing_comma를_보정한다() -> None:
    payload = load_json_object_response(
        """
        {
          "agenda": "회의록 점검",
          "items": [
            {"text": "마지막 comma 보정",},
          ],
        }
        """
    )

    assert payload == {
        "agenda": "회의록 점검",
        "items": [{"text": "마지막 comma 보정"}],
    }


def test_load_json_object_response는_object가_아니면_거부한다() -> None:
    with pytest.raises(ValueError):
        load_json_object_response('["object가 아닌 응답"]')


def test_load_json_value_response는_list_root도_파싱한다() -> None:
    payload = load_json_value_response(
        """
        ```json
        [
          {"event_type": "question", "title": "일정은 언제인가요?",},
        ]
        ```
        """
    )

    assert payload == [
        {"event_type": "question", "title": "일정은 언제인가요?"},
    ]
