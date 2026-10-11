"""Markdown retrieval chunker."""

from __future__ import annotations

import re
from dataclasses import dataclass


HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(?P<title>.+?)\s*$")


@dataclass(frozen=True)
class ChunkDraft:
    """embedding 전 단계 chunk 초안."""

    heading: str | None
    text: str


class MarkdownChunker:
    """heading-aware 규칙으로 markdown을 retrieval chunk로 분리한다."""

    def __init__(self, *, target_chars: int = 1000, overlap_chars: int = 160) -> None:
        self._target_chars = max(target_chars, 200)
        self._overlap_chars = max(min(overlap_chars, self._target_chars // 2), 0)

    def chunk(self, markdown: str) -> list[ChunkDraft]:
        sections = self._split_sections(markdown)
        chunks: list[ChunkDraft] = []
        for heading, section_text in sections:
            chunks.extend(self._slice_section(heading=heading, text=section_text))
        return [chunk for chunk in chunks if chunk.text.strip()]

    def _split_sections(self, markdown: str) -> list[tuple[str | None, str]]:
        lines = markdown.splitlines()
        sections: list[tuple[str | None, list[str]]] = []
        current_heading: str | None = None
        current_lines: list[str] = []

        for line in lines:
            matched = HEADING_PATTERN.match(line)
            if matched:
                if current_lines:
                    sections.append((current_heading, current_lines))
                current_heading = matched.group("title").strip()
                current_lines = [line]
                continue
            current_lines.append(line)

        if current_lines:
            sections.append((current_heading, current_lines))

        normalized_sections: list[tuple[str | None, str]] = []
        for heading, section_lines in sections:
            text = "\n".join(section_lines).strip()
            if text:
                normalized_sections.append((heading, text))
        return normalized_sections or [(None, markdown.strip())]

    def _slice_section(self, *, heading: str | None, text: str) -> list[ChunkDraft]:
        if len(text) <= self._target_chars:
            return [ChunkDraft(heading=heading, text=text.strip())]

        drafts: list[ChunkDraft] = []
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
                drafts.append(ChunkDraft(heading=heading, text=chunk_text))
            if end >= total_length:
                break
            start = max(end - self._overlap_chars, start + 1)
        return drafts
