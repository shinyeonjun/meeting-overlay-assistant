"""Assistant RAG context ranking."""

from __future__ import annotations

from dataclasses import dataclass
import re

from server.app.domain.retrieval import RetrievalSearchResult


_SECTION_ROLE_TERMS = {
    "action_item": (
        "action",
        "todo",
        "\uc561\uc158",
        "\ud560\uc77c",
        "\ub2e4\uc74c\ud560\uc77c",
        "\ud574\uc57c\ud560\uc77c",
        "\ub2f4\ub2f9",
        "\uae30\ud55c",
    ),
    "decision": (
        "decision",
        "\uacb0\uc815",
        "\uacb0\uc815\uc0ac\ud56d",
        "\ud569\uc758",
        "\uc815\ud55c",
    ),
    "risk": (
        "risk",
        "\ub9ac\uc2a4\ud06c",
        "\uc704\ud5d8",
        "\uc774\uc288",
        "\ubb38\uc81c",
        "\uc6b0\ub824",
    ),
    "question": (
        "openquestion",
        "\uc9c8\ubb38",
        "\ubbf8\ud574\uacb0",
        "\ub0a8\uc740\uc9c8\ubb38",
        "\ud655\uc778\ud560",
    ),
    "summary": (
        "summary",
        "\uc694\uc57d",
        "\uc815\ub9ac",
        "\ud575\uc2ec",
    ),
    "discussion": (
        "discussion",
        "\ub17c\uc758",
        "\uc598\uae30",
        "\uc774\uc57c\uae30",
        "\ud68c\uc758\ub0b4\uc6a9",
    ),
    "transcript": (
        "transcript",
        "\uc6d0\ubb38",
        "\ubc1c\uc5b8",
        "\uc804\uc0ac",
        "\ub204\uac00\ub9d0",
    ),
}

_DOCUMENT_QUERY_TERMS = {
    "document",
    "documents",
    "docs",
    "doc",
    "file",
    "files",
    "material",
    "materials",
    "\ubb38\uc11c",
    "\uc790\ub8cc",
    "\ud30c\uc77c",
}

_SOURCE_TYPE_PRIORITIES = {
    "report": -0.03,
    "session_summary": -0.025,
    "note": -0.01,
}

_RELEVANCE_SCORE_SPREAD_LIMIT = 0.34
_MIN_CONTEXT_SOURCES = 2


@dataclass(frozen=True)
class _RankedCandidate:
    score: float
    index: int
    result: RetrievalSearchResult
    tokens: frozenset[str]


def select_context_sources(
    *,
    query: str,
    search_query: str,
    candidates: list[RetrievalSearchResult],
    limit: int,
) -> list[RetrievalSearchResult]:
    """Rank and deduplicate candidate chunks for the answer context."""

    query_text = " ".join([query, search_query])
    tokens = _extract_query_tokens(query_text)
    requested_roles = _infer_requested_section_roles(query_text)
    seen: set[str] = set()
    ranked: list[_RankedCandidate] = []
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

        score = _base_rank_score(candidate)
        searchable = " ".join(
            [
                candidate.document_title,
                candidate.chunk_heading or "",
                candidate.chunk_text[:500],
            ]
        ).casefold()
        heading_text = (candidate.chunk_heading or "").casefold()
        title_text = candidate.document_title.casefold()
        for token in tokens:
            if token in heading_text:
                score -= 0.18
            elif token in title_text:
                score -= 0.08
            elif token in searchable:
                score -= 0.04

        section_role = _metadata_string(candidate, "section_role")
        if section_role and section_role in requested_roles:
            score -= 0.16
        if section_role == "transcript" and "transcript" not in requested_roles:
            score += 0.16
        if _is_document_source(candidate) and _is_document_query(tokens):
            score -= 0.08
        if candidate.speaker_label and any(
            token in candidate.speaker_label.casefold() for token in tokens
        ):
            score -= 0.06
        score += _SOURCE_TYPE_PRIORITIES.get(candidate.source_type, 0.0)
        ranked.append(
            _RankedCandidate(
                score=score,
                index=index,
                result=candidate,
                tokens=frozenset(_extract_text_tokens(searchable)),
            )
        )

    ranked.sort(key=lambda item: (item.score, item.index))
    eligible = _filter_relevant_candidates(ranked, limit)
    return [item.result for item in _select_diverse_candidates(eligible, limit)]


def _extract_query_tokens(query: str) -> list[str]:
    tokens = []
    seen = set()
    for token in re.findall(r"[0-9A-Za-z\uac00-\ud7a3]{2,}", query.casefold()):
        for candidate in _expand_query_token(token):
            if candidate in seen:
                continue
            seen.add(candidate)
            tokens.append(candidate)
    return tokens[:12]


def _expand_query_token(token: str) -> list[str]:
    expanded = [token]
    if re.fullmatch(r"[\uac00-\ud7a3]{3,}", token):
        expanded.append(token[:2])
    return expanded


def _extract_text_tokens(text: str) -> set[str]:
    return set(re.findall(r"[0-9A-Za-z\uac00-\ud7a3]{2,}", text.casefold()))


def _select_diverse_candidates(
    ranked: list[_RankedCandidate],
    limit: int,
) -> list[_RankedCandidate]:
    if limit <= 0:
        return []

    selected: list[_RankedCandidate] = []
    remaining = ranked[:]
    while remaining and len(selected) < limit:
        next_item = min(
            remaining,
            key=lambda item: (
                item.score + _diversity_penalty(item, selected),
                item.index,
            ),
        )
        selected.append(next_item)
        remaining.remove(next_item)
    return selected


def _filter_relevant_candidates(
    ranked: list[_RankedCandidate],
    limit: int,
) -> list[_RankedCandidate]:
    if not ranked:
        return []

    best_score = ranked[0].score
    cutoff = best_score + _RELEVANCE_SCORE_SPREAD_LIMIT
    eligible = [item for item in ranked if item.score <= cutoff]
    minimum = min(limit, _MIN_CONTEXT_SOURCES, len(ranked))
    if len(eligible) < minimum:
        return ranked[:minimum]
    return eligible


def _diversity_penalty(
    candidate: _RankedCandidate,
    selected: list[_RankedCandidate],
) -> float:
    if not selected:
        return 0.0

    penalty = 0.0
    same_document_count = sum(
        1 for item in selected if item.result.document_id == candidate.result.document_id
    )
    if same_document_count:
        penalty += min(same_document_count, 4) * 0.045

    for item in selected:
        if item.result.document_id == candidate.result.document_id:
            if (item.result.chunk_heading or "") == (candidate.result.chunk_heading or ""):
                penalty += 0.09
            if item.result.source_ref and item.result.source_ref == candidate.result.source_ref:
                penalty += 0.05

        overlap = _jaccard(candidate.tokens, item.tokens)
        if overlap >= 0.72:
            penalty += 0.14
        elif overlap >= 0.45:
            penalty += 0.08
        elif overlap >= 0.28:
            penalty += 0.04
    return penalty


def _jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    if not left or not right:
        return 0.0
    intersection = len(left & right)
    if intersection == 0:
        return 0.0
    return intersection / len(left | right)


def _infer_requested_section_roles(query: str) -> set[str]:
    compact = re.sub(r"\s+", "", query.casefold())
    return {
        role
        for role, terms in _SECTION_ROLE_TERMS.items()
        if any(term in compact for term in terms)
    }


def _metadata_string(candidate: RetrievalSearchResult, key: str) -> str:
    metadata = candidate.metadata_json or {}
    value = metadata.get(key)
    return str(value).strip().casefold() if value is not None else ""


def _base_rank_score(candidate: RetrievalSearchResult) -> float:
    if candidate.rank_score is not None:
        return -float(candidate.rank_score)
    return float(candidate.distance)


def _is_document_source(candidate: RetrievalSearchResult) -> bool:
    return (
        candidate.source_type == "document"
        or _metadata_string(candidate, "source_kind") == "document"
    )


def _is_document_query(tokens: list[str]) -> bool:
    return any(token in _DOCUMENT_QUERY_TERMS for token in tokens)
