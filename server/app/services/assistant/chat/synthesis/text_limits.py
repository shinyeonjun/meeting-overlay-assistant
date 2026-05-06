"""assistant 답변 context 크기 제한."""

from __future__ import annotations

MAX_CONTEXT_TEXT_CHARS = 900


def truncate_text(text: str) -> str:
    """프롬프트 context 크기를 제한한다."""

    normalized = " ".join(text.split())
    if len(normalized) <= MAX_CONTEXT_TEXT_CHARS:
        return normalized
    return normalized[: MAX_CONTEXT_TEXT_CHARS - 1].rstrip() + "…"
