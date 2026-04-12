"""리포트 영역의 markdown postprocess 서비스를 제공한다."""
from __future__ import annotations

from server.app.services.reports.refinement.llm_helpers.rules import (
    LIST_ITEM_PATTERN,
    REQUIRED_SECTION_HEADINGS,
    SECTION_HEADING_PATTERN,
    SECTION_HEADING_RULES,
    SECTION_SPLIT_PATTERN,
    SECTION_STYLE_RULES,
    SESSION_ID_LINE_RULES,
    SESSION_ID_PATTERN,
    TOP_LEVEL_HEADING_PATTERN,
    TOP_LEVEL_HEADING_RULES,
    TOP_LEVEL_ITEM_PATTERN,
)


def looks_like_markdown_report(content: str) -> bool:
    """LLM 응답이 리포트 형태인지 대략 판별한다."""

    stripped = content.lstrip()
    if not stripped:
        return False
    if stripped.startswith("{") or stripped.startswith("["):
        return False
    if stripped.startswith("```"):
        return False
    if not TOP_LEVEL_HEADING_PATTERN.search(stripped):
        return False
    return bool(SECTION_HEADING_PATTERN.search(stripped) or LIST_ITEM_PATTERN.search(stripped))


def normalize_markdown_headings(content: str) -> str:
    """영문/비표준 헤더를 한국 표준 헤더로 정규화한다."""

    normalized_lines: list[str] = []
    for line in content.splitlines():
        normalized_line = line

        for pattern, replacement in TOP_LEVEL_HEADING_RULES:
            if pattern.match(normalized_line):
                normalized_line = replacement
                break

        for pattern, replacement in SECTION_HEADING_RULES:
            if pattern.match(normalized_line):
                normalized_line = replacement
                break

        for pattern in SESSION_ID_LINE_RULES:
            match = pattern.match(normalized_line)
            if match is not None:
                normalized_line = f"- 세션 ID: {match.group(1).strip()}"
                break

        normalized_lines.append(normalized_line)

    return "\n".join(normalized_lines).strip()


def normalize_section_bullets(content: str) -> str:
    """섹션별 목록 스타일을 표준 형식으로 정규화한다."""

    lines = content.splitlines()
    normalized_lines: list[str] = []
    current_section: str | None = None
    item_index = 0

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("## "):
            current_section = stripped
            item_index = 0
            normalized_lines.append(stripped)
            continue

        if not stripped:
            normalized_lines.append("")
            continue

        if current_section is None or stripped.startswith("# "):
            normalized_lines.append(line)
            continue

        if SESSION_ID_PATTERN.match(stripped):
            normalized_lines.append(f"- 세션 ID: {stripped.split(':', 1)[1].strip()}")
            continue

        if line.startswith("  "):
            normalized_lines.append(line)
            continue

        style = SECTION_STYLE_RULES.get(current_section)
        if style is None:
            normalized_lines.append(line)
            continue

        item_text = extract_item_text(stripped)
        if not item_text:
            normalized_lines.append(line)
            continue

        if item_text == "없음":
            normalized_lines.append("- 없음")
            continue

        item_index += 1
        normalized_lines.append(format_item(style, item_index, item_text))

    return "\n".join(normalized_lines).strip()


def repair_markdown_report(content: str, fallback_markdown: str) -> str:
    """누락된 섹션과 세션 ID를 fallback 기반으로 보정한다."""

    normalized = content.strip()
    if not normalized:
        return fallback_markdown

    fallback_sections = extract_sections(fallback_markdown)
    repaired = normalized

    if not SESSION_ID_PATTERN.search(repaired):
        repaired = inject_session_id_line(repaired, fallback_markdown)

    missing_sections = [
        heading
        for heading in REQUIRED_SECTION_HEADINGS
        if heading not in repaired
    ]
    if not missing_sections:
        return repaired

    appended_blocks = [
        fallback_sections[heading]
        for heading in missing_sections
        if heading in fallback_sections
    ]
    if not appended_blocks:
        return repaired

    return f"{repaired}\n\n" + "\n\n".join(appended_blocks)


def extract_item_text(stripped_line: str) -> str:
    """목록 접두어를 제거한 본문을 추출한다."""

    match = TOP_LEVEL_ITEM_PATTERN.match(stripped_line)
    if match is None:
        return stripped_line
    return match.group(1).strip()


def format_item(style: str, item_index: int, item_text: str) -> str:
    """섹션 스타일에 맞춰 목록 항목을 재포맷한다."""

    if style == "numbered":
        return f"{item_index}. {item_text}"
    if style == "checkbox":
        import re

        checked_match = re.match(r"^\[[xX]\]\s+(.+)$", item_text)
        if checked_match is not None:
            return f"- [x] {checked_match.group(1).strip()}"
        unchecked_match = re.match(r"^\[\s\]\s+(.+)$", item_text)
        if unchecked_match is not None:
            return f"- [ ] {unchecked_match.group(1).strip()}"
        return f"- [ ] {item_text}"
    return f"- {item_text}"


def inject_session_id_line(content: str, fallback_markdown: str) -> str:
    """세션 ID 라인이 빠진 경우 fallback에서 주입한다."""

    fallback_lines = fallback_markdown.splitlines()
    session_line = next(
        (line for line in fallback_lines if SESSION_ID_PATTERN.match(line)),
        None,
    )
    if session_line is None:
        return content

    lines = content.splitlines()
    if not lines:
        return fallback_markdown

    insert_at = 1
    while insert_at < len(lines) and not lines[insert_at].strip():
        insert_at += 1

    new_lines = [lines[0], "", session_line, ""]
    new_lines.extend(lines[insert_at:])
    return "\n".join(new_lines).strip()


def extract_sections(content: str) -> dict[str, str]:
    """Markdown에서 섹션 블록을 추출한다."""

    parts = SECTION_SPLIT_PATTERN.split(content.strip())
    sections: dict[str, str] = {}
    for part in parts:
        block = part.strip()
        if not block.startswith("## "):
            continue
        heading = block.splitlines()[0].strip()
        sections[heading] = block
    return sections

