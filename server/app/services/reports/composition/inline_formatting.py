"""회의록 본문 인라인 강조 렌더링 helper."""

from __future__ import annotations

from html import escape as html_escape
from xml.sax.saxutils import escape as xml_escape


def render_html_inline(value: str, phrases: tuple[str, ...] = ()) -> str:
    """회의록 HTML 본문에 사용할 인라인 강조를 렌더링한다."""

    return _render_inline(
        value,
        phrases,
        escape_text=lambda text: html_escape(text, quote=True).replace("\n", "<br>"),
        open_tag='<strong class="report-keyword">',
        close_tag="</strong>",
    )


def render_reportlab_inline(value: str, phrases: tuple[str, ...] = ()) -> str:
    """ReportLab Paragraph에서 사용할 인라인 강조를 렌더링한다."""

    return _render_inline(
        value,
        phrases,
        escape_text=lambda text: xml_escape(str(text), {"\n": "<br/>"}),
        open_tag='<font color="#B42318"><b>',
        close_tag="</b></font>",
    )


def strip_inline_marks(value: str) -> str:
    """문서 본문에 남은 Markdown 강조 표식을 제거한 순수 텍스트를 반환한다."""

    text, _ = _extract_markdown_emphasis(value)
    return text


def _render_inline(
    value: str,
    phrases: tuple[str, ...],
    *,
    escape_text,
    open_tag: str,
    close_tag: str,
) -> str:
    plain_text, markdown_ranges = _extract_markdown_emphasis(value)
    ranges = _merge_ranges(
        [*markdown_ranges, *_highlight_ranges(plain_text, phrases)]
    )
    if not ranges:
        return escape_text(plain_text)

    chunks: list[str] = []
    cursor = 0
    for start, end in ranges:
        chunks.append(escape_text(plain_text[cursor:start]))
        chunks.append(open_tag)
        chunks.append(escape_text(plain_text[start:end]))
        chunks.append(close_tag)
        cursor = end
    chunks.append(escape_text(plain_text[cursor:]))
    return "".join(chunks)


def _extract_markdown_emphasis(value: str) -> tuple[str, list[tuple[int, int]]]:
    text = str(value)
    output: list[str] = []
    ranges: list[tuple[int, int]] = []
    input_index = 0
    output_index = 0

    while input_index < len(text):
        start = text.find("**", input_index)
        if start < 0:
            tail = text[input_index:].replace("**", "")
            output.append(tail)
            output_index += len(tail)
            break

        before = text[input_index:start]
        output.append(before)
        output_index += len(before)

        end = text.find("**", start + 2)
        if end < 0:
            tail = text[start:].replace("**", "")
            output.append(tail)
            output_index += len(tail)
            break

        marked = text[start + 2 : end]
        marked_start = output_index
        output.append(marked)
        output_index += len(marked)
        if marked.strip():
            ranges.append((marked_start, output_index))
        input_index = end + 2

    return "".join(output), ranges


def _highlight_ranges(value: str, phrases: tuple[str, ...]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for phrase in sorted(_valid_highlight_phrases(value, phrases), key=len, reverse=True):
        start = value.find(phrase)
        if start < 0:
            continue
        end = start + len(phrase)
        if any(
            _ranges_overlap(start, end, current_start, current_end)
            for current_start, current_end in ranges
        ):
            continue
        ranges.append((start, end))
    return sorted(ranges)


def _valid_highlight_phrases(value: str, phrases: tuple[str, ...]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    text = value.strip()
    for raw_phrase in phrases:
        phrase = " ".join(strip_inline_marks(str(raw_phrase)).split())
        if not phrase or len(phrase) < 2 or len(phrase) > 24 or phrase == text:
            continue
        if phrase not in value:
            continue
        key = phrase.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(phrase)
        if len(result) >= 3:
            break
    return result


def _merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(ranges):
        if start >= end:
            continue
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
            continue
        previous_start, previous_end = merged[-1]
        merged[-1] = (previous_start, max(previous_end, end))
    return merged


def _ranges_overlap(
    start: int,
    end: int,
    current_start: int,
    current_end: int,
) -> bool:
    return start < current_end and end > current_start
