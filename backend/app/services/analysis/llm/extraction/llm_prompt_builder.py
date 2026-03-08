"""LLM 인사이트 추출 프롬프트 생성기."""

from __future__ import annotations

import json
from pathlib import Path

from backend.app.services.analysis.llm.contracts.llm_models import LLMAnalysisInput
from backend.app.services.analysis.event_type_policy import (
    filter_insight_event_type_values,
)
from backend.app.services.analysis.llm.extraction.insight_extraction_spec import (
    InsightExtractionSpec,
    load_insight_extraction_spec,
)


class LLMAnalysisPromptBuilder:
    """발화 분석 프롬프트를 생성한다."""

    def __init__(
        self,
        *,
        spec: InsightExtractionSpec | None = None,
        spec_path: str | Path | None = None,
    ) -> None:
        self._spec = spec or load_insight_extraction_spec(spec_path)
        self._event_types = filter_insight_event_type_values(self._spec.event_types)

    def build(self, analysis_input: LLMAnalysisInput) -> str:
        """LLM에 전달할 분석 프롬프트를 만든다."""
        input_payload = {
            "session_id": analysis_input.session_id,
            "utterance_id": analysis_input.utterance_id,
            "text": analysis_input.text,
        }
        return "\n".join(
            [
                self._spec.instruction,
                "출력은 반드시 JSON 객체 하나만 반환한다.",
                f"최대 후보 개수: {self._spec.max_candidates}",
                f"허용 event_type: {', '.join(self._event_types)}",
                f"허용 state: {', '.join(self._spec.states)}",
                "출력 형식:",
                '{"candidates":[{"event_type":"...","title":"...","state":"...","priority":0,"body":null,"assignee":null,"due_date":null,"topic_group":null}]}',
                "근거가 약하면 candidates를 빈 배열로 반환한다.",
                "예시:",
                *[
                    json.dumps(example, ensure_ascii=False)
                    for example in self._spec.few_shot_examples
                ],
                "입력:",
                json.dumps(input_payload, ensure_ascii=False),
            ]
        )
