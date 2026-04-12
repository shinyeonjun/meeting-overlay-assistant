"""공통 영역의 llm response parser 서비스를 제공한다."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from server.app.services.analysis.event_type_policy import (
    filter_insight_event_type_values,
    normalize_event_type_token,
)
from server.app.services.analysis.llm.contracts.llm_models import (
    LLMAnalysisResult,
    LLMEventCandidate,
)
from server.app.services.analysis.llm.extraction.insight_extraction_spec import (
    InsightExtractionSpec,
    load_insight_extraction_spec,
)
from server.app.services.analysis.observability import (
    record_insight_candidate_dropped,
    record_insight_parse_failure,
)


logger = logging.getLogger(__name__)


class LLMAnalysisResponseParser:
    """문자열 응답을 LLMAnalysisResult로 변환한다."""

    def __init__(
        self,
        *,
        spec: InsightExtractionSpec | None = None,
        spec_path: str | Path | None = None,
    ) -> None:
        self._spec = spec or load_insight_extraction_spec(spec_path)
        self._allowed_event_types = set(
            filter_insight_event_type_values(self._spec.event_types)
        )
        self._allowed_states = set(self._spec.states)

    def parse(self, response_text: str) -> LLMAnalysisResult:
        """응답 JSON 문자열을 파싱한다."""

        payload = self._load_json_payload(response_text)
        if payload is None:
            record_insight_parse_failure("json_payload_unavailable")
            return LLMAnalysisResult()

        if isinstance(payload, list):
            candidates_data = payload
        elif isinstance(payload, dict):
            candidates_data = payload.get("candidates", [])
        else:
            record_insight_parse_failure("unexpected_payload_type")
            return LLMAnalysisResult()

        if not isinstance(candidates_data, list):
            record_insight_parse_failure("candidates_not_list")
            return LLMAnalysisResult()

        candidates: list[LLMEventCandidate] = []
        seen_keys: set[tuple[str, str]] = set()
        for item in candidates_data:
            parsed_candidate = self._parse_candidate(item)
            if parsed_candidate is None:
                continue
            dedup_key = (
                parsed_candidate.event_type,
                self._normalize_title(parsed_candidate.title),
            )
            if dedup_key in seen_keys:
                record_insight_candidate_dropped("duplicate_candidate")
                continue
            seen_keys.add(dedup_key)
            candidates.append(parsed_candidate)
            if len(candidates) >= self._spec.max_candidates:
                overflow_count = len(candidates_data) - len(candidates)
                if overflow_count > 0:
                    record_insight_candidate_dropped("max_candidates_exceeded")
                break

        return LLMAnalysisResult(candidates=candidates)

    def _parse_candidate(self, item: object) -> LLMEventCandidate | None:
        if not isinstance(item, dict):
            record_insight_candidate_dropped("candidate_not_object")
            return None

        event_type = normalize_event_type_token(item.get("event_type"))
        if event_type not in self._allowed_event_types:
            record_insight_candidate_dropped("invalid_event_type")
            return None

        raw_title = item.get("title")
        if not isinstance(raw_title, str):
            record_insight_candidate_dropped("title_not_string")
            return None
        title = raw_title.strip()
        if not title:
            record_insight_candidate_dropped("empty_title")
            return None

        state = self._normalize_token(item.get("state"))
        if state not in self._allowed_states:
            state = self._spec.default_state_by_event_type.get(event_type)
        if state not in self._allowed_states:
            record_insight_candidate_dropped("invalid_state")
            return None

        return LLMEventCandidate(
            event_type=event_type,
            title=title,
            state=state,
            body=self._nullable_string(item.get("body")),
        )

    @staticmethod
    def _normalize_token(value: object) -> str:
        if not isinstance(value, str):
            return ""
        return value.strip().lower().replace(" ", "_")

    @staticmethod
    def _nullable_string(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _normalize_title(title: str) -> str:
        compact = re.sub(r"\s+", " ", title.strip().lower())
        return re.sub(r"[^\w가-힣]+", "", compact)

    def _load_json_payload(self, response_text: str) -> object | None:
        text = (response_text or "").strip()
        if not text:
            logger.debug("LLM 응답 본문이 비어 있습니다.")
            return None

        direct = self._try_load_json(text)
        if direct is not None:
            return direct

        unwrapped = self._unwrap_markdown_fence(text)
        if unwrapped != text:
            fenced = self._try_load_json(unwrapped)
            if fenced is not None:
                return fenced

        start_candidates = [index for index in (text.find("{"), text.find("[")) if index != -1]
        if not start_candidates:
            return None
        start = min(start_candidates)
        end_candidates = [index for index in (text.rfind("}"), text.rfind("]")) if index != -1]
        if not end_candidates:
            return None
        end = max(end_candidates)
        if end <= start:
            return None
        return self._try_load_json(text[start : end + 1])

    @staticmethod
    def _try_load_json(text: str) -> object | None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _unwrap_markdown_fence(text: str) -> str:
        if not text.startswith("```"):
            return text
        lines = text.splitlines()
        if len(lines) < 3:
            return text
        if not lines[-1].strip().startswith("```"):
            return text
        return "\n".join(lines[1:-1]).strip()
