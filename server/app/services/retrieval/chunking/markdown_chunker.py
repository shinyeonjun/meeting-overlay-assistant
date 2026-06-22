"""Markdown retrieval chunker."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(?P<title>.+?)\s*$")


@dataclass(frozen=True)
class ChunkDraft:
    """embedding 전 단계 chunk 초안."""

    heading: str | None
    text: str
    source_ref: str | None = None
    speaker_label: str | None = None
    start_ms: int | None = None
    end_ms: int | None = None
    metadata_json: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class _SectionDraft:
    heading: str | None
    heading_path: tuple[str, ...]
    heading_level: int | None
    text: str
    section_index: int


class MarkdownChunker:
    """heading-aware 규칙으로 markdown을 retrieval chunk로 분리한다."""

    def __init__(
        self,
        *,
        target_chars: int = 1000,
        overlap_chars: int = 160,
        strategy_name: str = "markdown_heading",
    ) -> None:
        self._target_chars = max(target_chars, 200)
        self._overlap_chars = max(min(overlap_chars, self._target_chars // 2), 0)
        self._strategy_name = strategy_name

    @property
    def signature(self) -> str:
        return (
            f"{self._strategy_name}:target={self._target_chars}:"
            f"overlap={self._overlap_chars}"
        )

    def chunk(self, markdown: str) -> list[ChunkDraft]:
        sections = self._split_sections(markdown)
        chunks: list[ChunkDraft] = []
        for section in sections:
            chunks.extend(self._slice_section(section=section))
        return [chunk for chunk in chunks if chunk.text.strip()]

    def _split_sections(self, markdown: str) -> list[_SectionDraft]:
        lines = markdown.splitlines()
        sections: list[tuple[str | None, tuple[str, ...], int | None, list[str]]] = []
        current_heading: str | None = None
        current_heading_path: tuple[str, ...] = ()
        current_heading_level: int | None = None
        current_lines: list[str] = []
        heading_stack: list[str] = []

        for line in lines:
            matched = HEADING_PATTERN.match(line)
            if matched:
                if current_lines:
                    sections.append(
                        (
                            current_heading,
                            current_heading_path,
                            current_heading_level,
                            current_lines,
                        )
                    )
                current_heading_level = len(matched.group(1))
                current_heading = matched.group("title").strip()
                heading_stack = heading_stack[: current_heading_level - 1]
                heading_stack.append(current_heading)
                current_heading_path = tuple(heading_stack)
                current_lines = [line]
                continue
            current_lines.append(line)

        if current_lines:
            sections.append(
                (
                    current_heading,
                    current_heading_path,
                    current_heading_level,
                    current_lines,
                )
            )

        normalized_sections: list[_SectionDraft] = []
        for section_index, (heading, heading_path, heading_level, section_lines) in enumerate(
            sections
        ):
            text = "\n".join(section_lines).strip()
            if text:
                normalized_sections.append(
                    _SectionDraft(
                        heading=heading,
                        heading_path=heading_path,
                        heading_level=heading_level,
                        text=text,
                        section_index=section_index,
                    )
                )
        return normalized_sections or [
            _SectionDraft(
                heading=None,
                heading_path=(),
                heading_level=None,
                text=markdown.strip(),
                section_index=0,
            )
        ]

    def _slice_section(self, *, section: _SectionDraft) -> list[ChunkDraft]:
        text = section.text
        if len(text) <= self._target_chars:
            return [
                ChunkDraft(
                    heading=section.heading,
                    text=text.strip(),
                    metadata_json=_build_chunk_metadata(
                        section=section,
                        chunk_ordinal=0,
                        chunk_count=1,
                        chunk_strategy=self._strategy_name,
                        target_chars=self._target_chars,
                        overlap_chars=self._overlap_chars,
                    ),
                )
            ]

        chunk_texts: list[str] = []
        start = 0
        total_length = len(text)
        while start < total_length:
            end = min(start + self._target_chars, total_length)
            if end < total_length:
                preferred_break = text.rfind("\n", start, end)
                if preferred_break >= start + int(self._target_chars * 0.6):
                    end = preferred_break
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunk_texts.append(chunk_text)
            if end >= total_length:
                break
            start = max(end - self._overlap_chars, start + 1)
        chunk_count = len(chunk_texts)
        return [
            ChunkDraft(
                heading=section.heading,
                text=chunk_text,
                metadata_json=_build_chunk_metadata(
                    section=section,
                    chunk_ordinal=index,
                    chunk_count=chunk_count,
                    chunk_strategy=self._strategy_name,
                    target_chars=self._target_chars,
                    overlap_chars=self._overlap_chars,
                ),
            )
            for index, chunk_text in enumerate(chunk_texts)
        ]


def _build_chunk_metadata(
    *,
    section: _SectionDraft,
    chunk_ordinal: int,
    chunk_count: int,
    chunk_strategy: str,
    target_chars: int,
    overlap_chars: int,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "section_index": section.section_index,
        "chunk_ordinal": chunk_ordinal,
        "chunk_count": chunk_count,
        "chunk_strategy": chunk_strategy,
        "chunk_target_chars": target_chars,
        "chunk_overlap_chars": overlap_chars,
    }
    if section.heading:
        metadata["section_heading"] = section.heading
    if section.heading_path:
        metadata["heading_path"] = list(section.heading_path)
    if section.heading_level is not None:
        metadata["heading_level"] = section.heading_level
    section_role = _classify_section_role(section.heading_path or (section.heading or "",))
    if section_role:
        metadata["section_role"] = section_role
    return metadata


def _classify_section_role(heading_path: tuple[str, ...]) -> str | None:
    heading_text = " ".join(heading_path).casefold()
    compact = re.sub(r"\s+", "", heading_text)
    role_terms = (
        ("action_item", ("액션", "할일", "다음할일", "todo", "action", "followup")),
        ("decision", ("결정", "결정사항", "합의", "decision")),
        ("risk", ("리스크", "위험", "이슈", "특이사항", "risk")),
        ("question", ("질문", "미해결", "openquestion", "q&a")),
        ("summary", ("요약", "핵심", "summary")),
        ("discussion", ("논의", "회의내용", "discussion")),
        ("transcript", ("전사", "발화", "transcript")),
    )
    for role, terms in role_terms:
        if any(term in compact or term in heading_text for term in terms):
            return role
    return None
