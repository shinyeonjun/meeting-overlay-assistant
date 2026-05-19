"""LLM JSON 응답 파싱 유틸리티."""

from __future__ import annotations

import json


def load_json_value_response(response_text: str) -> object:
    """LLM 응답 문자열에서 JSON value를 보수적으로 파싱한다."""

    try:
        return json.loads(response_text)
    except json.JSONDecodeError as first_error:
        extracted = _extract_json_value(response_text)
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            repaired = _strip_json_trailing_commas(extracted)
            if repaired == extracted:
                raise first_error
            return json.loads(repaired)


def load_json_object_response(response_text: str) -> dict[str, object]:
    """LLM 응답 문자열에서 JSON object를 보수적으로 파싱한다."""

    payload = load_json_value_response(response_text)
    if not isinstance(payload, dict):
        raise ValueError("LLM 응답은 JSON object여야 합니다.")
    return payload


def _strip_json_trailing_commas(value: str) -> str:
    result: list[str] = []
    in_string = False
    escaped = False
    index = 0
    while index < len(value):
        char = value[index]
        if in_string:
            result.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue

        if char == '"':
            in_string = True
            result.append(char)
            index += 1
            continue

        if char == ",":
            lookahead = index + 1
            while lookahead < len(value) and value[lookahead].isspace():
                lookahead += 1
            if lookahead < len(value) and value[lookahead] in "]}":
                index += 1
                continue

        result.append(char)
        index += 1
    return "".join(result)


def _extract_json_value(response_text: str) -> str:
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    start_candidates = [
        index for index in (cleaned.find("{"), cleaned.find("[")) if index >= 0
    ]
    if not start_candidates:
        raise json.JSONDecodeError("JSON value를 찾을 수 없습니다.", response_text, 0)

    start = min(start_candidates)
    closing_char = "}" if cleaned[start] == "{" else "]"
    end = cleaned.rfind(closing_char)
    if end <= start:
        raise json.JSONDecodeError("JSON value를 찾을 수 없습니다.", response_text, 0)
    return cleaned[start : end + 1]
