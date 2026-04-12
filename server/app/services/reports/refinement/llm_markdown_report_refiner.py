"""LLM 기반 Markdown 리포트 정제기."""

from __future__ import annotations

import re

from server.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)
from server.app.services.reports.refinement.report_refiner import (
    ReportRefinementInput,
    ReportRefiner,
)
from server.app.services.reports.refinement.structured_markdown_report_refiner import (
    StructuredMarkdownReportRefiner,
)


class LLMMarkdownReportRefiner(ReportRefiner):
    """LLM 응답을 우선 사용하되 헤더와 목록 스타일을 표준 형식으로 정리한다."""

    _TOP_LEVEL_HEADING_PATTERN = re.compile(r"^\s*#\s+\S", re.MULTILINE)
    _SECTION_HEADING_PATTERN = re.compile(r"^\s*##\s+\S", re.MULTILINE)
    _LIST_ITEM_PATTERN = re.compile(r"^\s*(?:[-*]|\d+\.)\s+\S", re.MULTILINE)
    _SESSION_ID_PATTERN = re.compile(r"^\s*-\s*세션\s*ID\s*:", re.MULTILINE)
    _SECTION_SPLIT_PATTERN = re.compile(r"(?=^##\s+)", re.MULTILINE)
    _SESSION_ID_LINE_RULES = (
        re.compile(r"^\s*-?\s*session\s*id\s*:\s*(.+?)\s*$", re.IGNORECASE),
        re.compile(r"^\s*-?\s*meeting\s*id\s*:\s*(.+?)\s*$", re.IGNORECASE),
    )
    _TOP_LEVEL_HEADING_RULES = (
        (re.compile(r"^\s*#\s*(?:session|meeting)\s+report\b.*$", re.IGNORECASE), "# 회의 리포트"),
        (re.compile(r"^\s*#\s*report\b.*$", re.IGNORECASE), "# 회의 리포트"),
    )
    _SECTION_HEADING_RULES = (
        (
            re.compile(r"^\s*##\s*(?:snapshot|overview|meeting overview)\s*$", re.IGNORECASE),
            "## 회의 개요",
        ),
        (
            re.compile(r"^\s*##\s*(?:questions?|open questions?)\s*$", re.IGNORECASE),
            "## 질문",
        ),
        (
            re.compile(r"^\s*##\s*(?:decisions?|decision log)\s*$", re.IGNORECASE),
            "## 결정 사항",
        ),
        (
            re.compile(r"^\s*##\s*(?:action items?|next steps?|todos?)\s*$", re.IGNORECASE),
            "## 액션 아이템",
        ),
        (
            re.compile(r"^\s*##\s*(?:risks?|concerns?)\s*$", re.IGNORECASE),
            "## 리스크",
        ),
        (
            re.compile(r"^\s*##\s*(?:transcript|reference transcript|notes?)\s*$", re.IGNORECASE),
            "## 참고 전사",
        ),
        (
            re.compile(
                r"^\s*##\s*(?:speaker insights?|insights?|observations?)\s*$",
                re.IGNORECASE,
            ),
            "## 발화자 기반 인사이트",
        ),
    )
    _REQUIRED_SECTION_HEADINGS = (
        "## 회의 개요",
        "## 질문",
        "## 결정 사항",
        "## 액션 아이템",
        "## 리스크",
        "## 참고 전사",
        "## 발화자 기반 인사이트",
    )
    _SECTION_STYLE_RULES = {
        "## 회의 개요": "bullet",
        "## 질문": "bullet",
        "## 결정 사항": "numbered",
        "## 액션 아이템": "checkbox",
        "## 리스크": "bullet",
        "## 참고 전사": "bullet",
        "## 발화자 기반 인사이트": "bullet",
    }
    _TOP_LEVEL_ITEM_PATTERN = re.compile(
        r"^\s*(?:[-*]\s+|\d+[.)]\s+|\[[ xX]\]\s+|-\s*\[[ xX]\]\s+)?(.+?)\s*$"
    )

    def __init__(self, completion_client: LLMCompletionClient) -> None:
        self._completion_client = completion_client
        self._fallback_refiner = StructuredMarkdownReportRefiner()

    def refine(self, refinement_input: ReportRefinementInput) -> str:
        fallback_markdown = self._fallback_refiner.refine(refinement_input)
        prompt = self._build_prompt(refinement_input)
        try:
            refined_markdown = self._completion_client.complete(prompt).strip()
        except Exception:
            return fallback_markdown

        if not refined_markdown:
            return fallback_markdown

        normalized_markdown = self._normalize_markdown_headings(refined_markdown)
        if not self._looks_like_markdown_report(normalized_markdown):
            return fallback_markdown

        normalized_bullets = self._normalize_section_bullets(normalized_markdown)
        return self._repair_markdown_report(normalized_bullets, fallback_markdown)

    def _build_prompt(self, refinement_input: ReportRefinementInput) -> str:
        event_block = "\n".join(f"- {line}" for line in refinement_input.event_lines) or "- 없음"
        transcript_block = (
            "\n".join(f"- {line}" for line in refinement_input.speaker_transcript_lines)
            or "- 없음"
        )
        speaker_event_block = (
            "\n".join(f"- {line}" for line in refinement_input.speaker_event_lines)
            or "- 없음"
        )

        return (
            "당신은 회의 리포트를 정리하는 전문 편집자다.\n"
            "아래 자료를 바탕으로 사용자가 바로 읽을 수 있는 수준의 Markdown 리포트를 작성하라.\n"
            "반드시 Markdown만 반환하고, 설명 문장이나 코드 블록은 추가하지 마라.\n"
            "\n"
            "섹션 순서는 반드시 아래를 따른다.\n"
            "1. # 회의 리포트\n"
            "2. - 세션 ID: ...\n"
            "3. ## 회의 개요\n"
            "4. ## 질문\n"
            "5. ## 결정 사항\n"
            "6. ## 액션 아이템\n"
            "7. ## 리스크\n"
            "8. ## 참고 전사\n"
            "9. ## 발화자 기반 인사이트\n"
            "\n"
            "규칙:\n"
            "- 내용이 없으면 '없음'이라고만 적는다.\n"
            "- 액션 아이템에 담당자나 기한이 있으면 함께 적는다.\n"
            "- 근거 문장이 있으면 해당 항목 아래에 정리한다.\n"
            "- 참고 전사는 중복을 줄이고 핵심 발화만 정리한다.\n"
            "- 없는 사실은 추가하지 마라.\n"
            "- 같은 내용을 여러 문장으로 반복하지 말고 자연스럽게 합쳐라.\n"
            "- 질문, 결정 사항, 액션 아이템, 리스크는 서로 섞지 마라.\n"
            "\n"
            f"세션 ID: {refinement_input.session_id}\n"
            "\n"
            "[원본 Markdown]\n"
            f"{refinement_input.raw_markdown}\n"
            "\n"
            "[이벤트]\n"
            f"{event_block}\n"
            "\n"
            "[발화 전사]\n"
            f"{transcript_block}\n"
            "\n"
            "[발화와 이벤트 연결]\n"
            f"{speaker_event_block}\n"
        )

    @classmethod
    def _looks_like_markdown_report(cls, content: str) -> bool:
        stripped = content.lstrip()
        if not stripped:
            return False
        if stripped.startswith("{") or stripped.startswith("["):
            return False
        if stripped.startswith("```"):
            return False
        if not cls._TOP_LEVEL_HEADING_PATTERN.search(stripped):
            return False
        return bool(
            cls._SECTION_HEADING_PATTERN.search(stripped)
            or cls._LIST_ITEM_PATTERN.search(stripped)
        )

    @classmethod
    def _normalize_markdown_headings(cls, content: str) -> str:
        normalized_lines: list[str] = []
        for line in content.splitlines():
            normalized_line = line

            for pattern, replacement in cls._TOP_LEVEL_HEADING_RULES:
                if pattern.match(normalized_line):
                    normalized_line = replacement
                    break

            for pattern, replacement in cls._SECTION_HEADING_RULES:
                if pattern.match(normalized_line):
                    normalized_line = replacement
                    break

            for pattern in cls._SESSION_ID_LINE_RULES:
                match = pattern.match(normalized_line)
                if match is not None:
                    normalized_line = f"- 세션 ID: {match.group(1).strip()}"
                    break

            normalized_lines.append(normalized_line)

        return "\n".join(normalized_lines).strip()

    @classmethod
    def _normalize_section_bullets(cls, content: str) -> str:
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

            if cls._SESSION_ID_PATTERN.match(stripped):
                normalized_lines.append(f"- 세션 ID: {stripped.split(':', 1)[1].strip()}")
                continue

            if line.startswith("  "):
                normalized_lines.append(line)
                continue

            style = cls._SECTION_STYLE_RULES.get(current_section)
            if style is None:
                normalized_lines.append(line)
                continue

            item_text = cls._extract_item_text(stripped)
            if not item_text:
                normalized_lines.append(line)
                continue

            if item_text == "없음":
                normalized_lines.append("- 없음")
                continue

            item_index += 1
            normalized_lines.append(cls._format_item(style, item_index, item_text))

        return "\n".join(normalized_lines).strip()

    @classmethod
    def _extract_item_text(cls, stripped_line: str) -> str:
        match = cls._TOP_LEVEL_ITEM_PATTERN.match(stripped_line)
        if match is None:
            return stripped_line
        return match.group(1).strip()

    @staticmethod
    def _format_item(style: str, item_index: int, item_text: str) -> str:
        if style == "numbered":
            return f"{item_index}. {item_text}"
        if style == "checkbox":
            checked_match = re.match(r"^\[[xX]\]\s+(.+)$", item_text)
            if checked_match is not None:
                return f"- [x] {checked_match.group(1).strip()}"
            unchecked_match = re.match(r"^\[\s\]\s+(.+)$", item_text)
            if unchecked_match is not None:
                return f"- [ ] {unchecked_match.group(1).strip()}"
            return f"- [ ] {item_text}"
        return f"- {item_text}"

    @classmethod
    def _repair_markdown_report(cls, content: str, fallback_markdown: str) -> str:
        normalized = content.strip()
        if not normalized:
            return fallback_markdown

        fallback_sections = cls._extract_sections(fallback_markdown)
        repaired = normalized

        if not cls._SESSION_ID_PATTERN.search(repaired):
            repaired = cls._inject_session_id_line(repaired, fallback_markdown)

        missing_sections = [
            heading
            for heading in cls._REQUIRED_SECTION_HEADINGS
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

    @classmethod
    def _inject_session_id_line(cls, content: str, fallback_markdown: str) -> str:
        fallback_lines = fallback_markdown.splitlines()
        session_line = next(
            (line for line in fallback_lines if cls._SESSION_ID_PATTERN.match(line)),
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

    @classmethod
    def _extract_sections(cls, content: str) -> dict[str, str]:
        parts = cls._SECTION_SPLIT_PATTERN.split(content.strip())
        sections: dict[str, str] = {}
        for part in parts:
            block = part.strip()
            if not block.startswith("## "):
                continue
            heading = block.splitlines()[0].strip()
            sections[heading] = block
        return sections
