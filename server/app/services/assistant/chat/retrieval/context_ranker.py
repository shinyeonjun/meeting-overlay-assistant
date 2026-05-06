"""assistant RAG context 재정렬."""

from __future__ import annotations

import re

from server.app.domain.retrieval import RetrievalSearchResult


def select_context_sources(
    *,
    query: str,
    search_query: str,
    candidates: list[RetrievalSearchResult],
    limit: int,
) -> list[RetrievalSearchResult]:
    """검색 후보를 중복 제거하고 문서/heading/text 관련도 기준으로 재정렬한다."""

    tokens = _extract_query_tokens(" ".join([query, search_query]))
    seen: set[str] = set()
    ranked: list[tuple[float, int, RetrievalSearchResult]] = []
    for index, candidate in enumerate(candidates):
        dedupe_key = "|".join(
            [
                candidate.document_id,
                candidate.chunk_heading or "",
                candidate.chunk_text[:120],
            ]
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        score = float(candidate.distance)
        searchable = " ".join(
            [
                candidate.document_title,
                candidate.chunk_heading or "",
                candidate.chunk_text[:500],
            ]
        ).lower()
        heading_text = (candidate.chunk_heading or "").lower()
        title_text = candidate.document_title.lower()
        for token in tokens:
            if token in heading_text:
                score -= 0.18
            elif token in title_text:
                score -= 0.08
            elif token in searchable:
                score -= 0.04
        if candidate.source_type == "report":
            score -= 0.02
        ranked.append((score, index, candidate))

    ranked.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in ranked[:limit]]


def _extract_query_tokens(query: str) -> list[str]:
    tokens = []
    seen = set()
    for token in re.findall(r"[0-9A-Za-z가-힣_]{2,}", query.lower()):
        for candidate in _expand_query_token(token):
            if candidate in seen:
                continue
            seen.add(candidate)
            tokens.append(candidate)
    return tokens[:12]


def _expand_query_token(token: str) -> list[str]:
    expanded = [token]
    if re.fullmatch(r"[가-힣]{3,}", token):
        expanded.append(token[:2])
    return expanded
