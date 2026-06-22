"""Transcript-aware retrieval chunker."""

from __future__ import annotations

import re
from dataclasses import dataclass

from server.app.services.retrieval.chunking.markdown_chunker import ChunkDraft, MarkdownChunker


TRANSCRIPT_LINE_PATTERN = re.compile(
    r"^-\s+\[(?P<start>\d{2}:\d{2}(?::\d{2})?)-(?P<end>\d{2}:\d{2}(?::\d{2})?)\]\s+"
    r"(?P<speaker>[^:]+):\s*(?P<text>.*)$"
)


@dataclass(frozen=True)
class _TranscriptTurn:
    line: str
    source_ref: str
    speaker_label: str
    start_ms: int
    end_ms: int


class TranscriptTurnChunker:
    """Chunk note transcripts on utterance boundaries before falling back to markdown."""

    def __init__(self, *, target_chars: int = 1400, overlap_chars: int = 220) -> None:
        self._target_chars = max(target_chars, 400)
        self._overlap_chars = max(min(overlap_chars, self._target_chars // 2), 0)
        self._fallback = MarkdownChunker(
            target_chars=target_chars,
            overlap_chars=overlap_chars,
            strategy_name="markdown_heading_fallback",
        )

    @property
    def signature(self) -> str:
        return (
            f"transcript_turn_boundary:target={self._target_chars}:"
            f"overlap={self._overlap_chars}:fallback={self._fallback.signature}"
        )

    def chunk(self, markdown: str) -> list[ChunkDraft]:
        turns = _extract_transcript_turns(markdown)
        if len(turns) < 2:
            return self._fallback.chunk(markdown)

        groups = self._group_turns(turns)
        chunk_count = len(groups)
        return [
            self._build_chunk(turns=group, chunk_ordinal=index, chunk_count=chunk_count)
            for index, group in enumerate(groups)
            if group
        ]

    def _group_turns(self, turns: list[_TranscriptTurn]) -> list[list[_TranscriptTurn]]:
        groups: list[list[_TranscriptTurn]] = []
        current: list[_TranscriptTurn] = []
        current_chars = 0

        for turn in turns:
            line_length = len(turn.line) + 1
            would_exceed = current and current_chars + line_length > self._target_chars
            if would_exceed:
                groups.append(current)
                current = self._build_overlap(current)
                current_chars = sum(len(item.line) + 1 for item in current)
                if current and current_chars + line_length > self._target_chars:
                    current = []
                    current_chars = 0

            current.append(turn)
            current_chars += line_length

        if current:
            groups.append(current)
        return groups

    def _build_overlap(self, turns: list[_TranscriptTurn]) -> list[_TranscriptTurn]:
        if not self._overlap_chars:
            return []

        overlap: list[_TranscriptTurn] = []
        total_chars = 0
        for turn in reversed(turns):
            next_total = total_chars + len(turn.line) + 1
            if overlap and next_total > self._overlap_chars:
                break
            overlap.append(turn)
            total_chars = next_total
        return list(reversed(overlap))

    def _build_chunk(
        self,
        *,
        turns: list[_TranscriptTurn],
        chunk_ordinal: int,
        chunk_count: int,
    ) -> ChunkDraft:
        speakers = {turn.speaker_label for turn in turns if turn.speaker_label}
        start_ms = min(turn.start_ms for turn in turns)
        end_ms = max(turn.end_ms for turn in turns)
        source_ref = f"{_format_ms(start_ms)}-{_format_ms(end_ms)}"

        return ChunkDraft(
            heading="Transcript",
            text="\n".join(turn.line for turn in turns).strip(),
            source_ref=source_ref,
            speaker_label=next(iter(speakers)) if len(speakers) == 1 else None,
            start_ms=start_ms,
            end_ms=end_ms,
            metadata_json={
                "section_heading": "Transcript",
                "heading_path": ["Note transcript", "Transcript"],
                "heading_level": 2,
                "section_role": "transcript",
                "chunk_strategy": "transcript_turn_boundary",
                "chunk_target_chars": self._target_chars,
                "chunk_overlap_chars": self._overlap_chars,
                "chunk_ordinal": chunk_ordinal,
                "chunk_count": chunk_count,
                "turn_count": len(turns),
                "source_ref": source_ref,
                "speakers": sorted(speakers),
            },
        )


def _extract_transcript_turns(markdown: str) -> list[_TranscriptTurn]:
    turns: list[_TranscriptTurn] = []
    for line in markdown.splitlines():
        normalized = line.strip()
        matched = TRANSCRIPT_LINE_PATTERN.match(normalized)
        if not matched:
            continue
        start_ms = _parse_timestamp_ms(matched.group("start"))
        end_ms = _parse_timestamp_ms(matched.group("end"))
        speaker_label = matched.group("speaker").strip()
        turns.append(
            _TranscriptTurn(
                line=normalized,
                source_ref=f"{matched.group('start')}-{matched.group('end')}",
                speaker_label=speaker_label,
                start_ms=start_ms,
                end_ms=max(end_ms, start_ms),
            )
        )
    return turns


def _parse_timestamp_ms(value: str) -> int:
    parts = [int(part) for part in value.split(":")]
    if len(parts) == 2:
        minutes, seconds = parts
        return (minutes * 60 + seconds) * 1000
    hours, minutes, seconds = parts
    return (hours * 3600 + minutes * 60 + seconds) * 1000


def _format_ms(value: int) -> str:
    total_seconds = max(0, value // 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"
