"""assistant 답변 fallback."""

from __future__ import annotations

from server.app.domain.retrieval import RetrievalSearchResult
from server.app.services.assistant.chat.synthesis.text_limits import truncate_text


def build_fallback_answer(sources: list[RetrievalSearchResult]) -> str:
    """LLM 답변 생성 실패 시 검색 근거 snippet만 안전하게 반환한다."""

    bullets = []
    for index, source in enumerate(sources[:3], start=1):
        snippet = truncate_text(source.chunk_text)
        bullets.append(f"- {snippet} [S{index}]")
    return "검색된 근거 기준으로는 다음 내용을 확인할 수 있습니다.\n\n" + "\n".join(bullets)
