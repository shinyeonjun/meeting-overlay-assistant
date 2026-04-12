"""오디오 영역의 preview stability 서비스를 제공한다."""
from __future__ import annotations

COMMIT_BOUNDARY_CHARS = {" ", ".", ",", "?", "!", ":", ";"}
COMPARISON_IGNORED_CHARS = COMMIT_BOUNDARY_CHARS | {"\n", "\t", '"', "'", "(", ")"}


def normalize_text(text: str) -> str:
    """비교용 텍스트를 정규화한다."""

    return " ".join(text.casefold().split())


def longest_common_prefix(values: list[str]) -> str:
    """문자열 목록의 최장 공통 prefix를 구한다."""

    if not values:
        return ""

    prefix = values[0]
    for candidate in values[1:]:
        limit = min(len(prefix), len(candidate))
        index = 0
        while index < limit and prefix[index] == candidate[index]:
            index += 1
        prefix = prefix[:index]
        if not prefix:
            break
    return prefix


def significant_text(text: str) -> str:
    """비교 시 무시할 문자를 제거한 핵심 텍스트를 만든다."""

    return "".join(
        char
        for char in text
        if char not in COMPARISON_IGNORED_CHARS and not char.isspace()
    )


def trim_to_commit_boundary(text: str, minimum_without_boundary: int) -> str:
    """commit 가능한 경계까지 텍스트를 잘라낸다."""

    if not text:
        return ""

    trimmed = text.strip()
    if not trimmed:
        return ""

    compact = significant_text(trimmed)
    if len(compact) >= minimum_without_boundary:
        return trimmed

    if trimmed[-1] in COMMIT_BOUNDARY_CHARS:
        return trimmed

    last_boundary = -1
    for boundary_char in COMMIT_BOUNDARY_CHARS:
        last_boundary = max(last_boundary, trimmed.rfind(boundary_char))

    if last_boundary > 0:
        return trimmed[:last_boundary].strip()
    return ""


def project_significant_prefix_to_text(text: str, significant_length: int) -> str:
    """핵심 prefix 길이를 원본 텍스트의 위치로 다시 투영한다."""

    if significant_length <= 0:
        return ""

    significant_seen = 0
    last_index = -1
    for index, char in enumerate(text):
        if char in COMPARISON_IGNORED_CHARS or char.isspace():
            continue
        significant_seen += 1
        last_index = index
        if significant_seen >= significant_length:
            break

    if last_index < 0:
        return ""

    return text[: last_index + 1].rstrip()
