"""OpenAI Responses API completion client."""

from __future__ import annotations

import os
from typing import Any

from server.app.services.analysis.event_type_policy import INSIGHT_EVENT_TYPE_VALUES
from server.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)


MEETING_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "event_type": {
                        "type": "string",
                        "enum": list(INSIGHT_EVENT_TYPE_VALUES),
                    },
                    "title": {"type": "string"},
                    "state": {"type": "string"},
                    "body": {"type": ["string", "null"]},
                },
                "required": ["event_type", "title", "state", "body"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["candidates"],
    "additionalProperties": False,
}


class OpenAIResponsesCompletionClient(LLMCompletionClient):
    """OpenAI Responses API를 이용해 JSON 문자열을 반환한다."""

    def __init__(self, model: str, sdk_client: object | None = None) -> None:
        self._model = model
        self._sdk_client = sdk_client

    def complete(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        response_schema: dict[str, Any] | None = None,
        keep_alive: str | None = None,
    ) -> str:
        """Responses API 호출 결과의 output_text를 반환한다."""
        del system_prompt, keep_alive
        client = self._sdk_client or self._create_sdk_client()
        schema: dict[str, Any] = response_schema or MEETING_ANALYSIS_SCHEMA
        response = client.responses.create(
            model=self._model,
            input=prompt,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "meeting_event_extraction",
                    "strict": True,
                    "schema": schema,
                }
            },
        )
        return getattr(response, "output_text", "") or ""

    def _create_sdk_client(self) -> object:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

        try:
            from openai import OpenAI
        except ImportError as error:
            raise RuntimeError("OpenAI SDK가 설치되지 않았습니다. `pip install openai`가 필요합니다.") from error

        return OpenAI(api_key=api_key)
