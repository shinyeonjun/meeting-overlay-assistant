"""streaming preview 안정화 공용 유틸."""

from __future__ import annotations

COMMIT_BOUNDARY_CHARS = {" ", ".", ",", "?", "!", ":", ";"}
STRONG_COMMIT_BOUNDARY_CHARS = {".", "?", "!"}
COMPARISON_IGNORED_CHARS = COMMIT_BOUNDARY_CHARS | {"\n", "\t", '"', "'", "(", ")"}
KOREAN_CONTINUATION_SUFFIXES = (
    "에게",
    "에서",
    "으로",
    "인데",
    "는데",
    "지만",
    "니까",
    "려고",
    "면서",
    "고",
    "서",
    "며",
    "면",
    "이",
    "가",
    "은",
    "는",
    "을",
    "를",
    "와",
    "과",
)
KOREAN_CONTINUATION_TOKENS = {
    "그리고",
    "근데",
    "그런데",
    "그래서",
    "그러면",
    "하지만",
    "또",
    "또는",
}


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


def _last_boundary_index(text: str, boundary_chars: set[str]) -> int:
    """지정한 boundary 문자 기준으로 마지막 경계를 찾는다."""

    last_boundary = -1
    for boundary_char in boundary_chars:
        last_boundary = max(last_boundary, text.rfind(boundary_char))
    return last_boundary


def _extract_last_token(text: str) -> str:
    """문장 끝의 마지막 어절 후보를 추출한다."""

    token_chars: list[str] = []
    for char in reversed(text.strip()):
        if char in COMMIT_BOUNDARY_CHARS or char.isspace():
            break
        token_chars.append(char)
    return "".join(reversed(token_chars)).strip()


def _looks_like_unfinished_korean_tail(text: str) -> bool:
    """한국어 문장 끝이 아직 이어질 가능성이 큰지 판단한다."""

    token = _extract_last_token(text)
    if not token:
        return False

    if token in KOREAN_CONTINUATION_TOKENS:
        return True

    if not any("\uac00" <= char <= "\ud7a3" for char in token):
        return False

    return any(token.endswith(suffix) for suffix in KOREAN_CONTINUATION_SUFFIXES)


def trim_to_commit_boundary(text: str, minimum_without_boundary: int) -> str:
    """commit 가능한 경계까지 텍스트를 잘라낸다."""

    if not text:
        return ""

    trimmed = text.strip()
    if not trimmed:
        return ""

    if trimmed[-1] in COMMIT_BOUNDARY_CHARS:
        return trimmed

    last_strong_boundary = _last_boundary_index(
        trimmed[:-1],
        STRONG_COMMIT_BOUNDARY_CHARS,
    )
    if last_strong_boundary >= 0:
        return trimmed[: last_strong_boundary + 1].strip()

    compact = significant_text(trimmed)
    if (
        len(compact) >= minimum_without_boundary
        and not _looks_like_unfinished_korean_tail(trimmed)
    ):
        return trimmed

    last_boundary = _last_boundary_index(trimmed, COMMIT_BOUNDARY_CHARS)
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
