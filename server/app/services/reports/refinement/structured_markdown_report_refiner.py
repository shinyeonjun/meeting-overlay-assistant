"""구조화된 Markdown 리포트 정제기."""

from __future__ import annotations

from collections import defaultdict
import re

from server.app.services.reports.refinement.report_refiner import (
    ReportRefinementEvent,
    ReportRefinementInput,
    ReportRefiner,
)


class StructuredMarkdownReportRefiner(ReportRefiner):
    """이벤트 메타데이터를 기반으로 사용자용 리포트를 구성한다."""

    _META_PATTERNS = (
        "질문하나더있습니다",
        "질문하나더합니다",
        "추가리스크도있습니다",
        "추가리스크확인필요",
        "추가질문",
    )

    def refine(self, refinement_input: ReportRefinementInput) -> str:
        cleaned_events = self._clean_events(refinement_input.events)
        grouped = self._group_events(cleaned_events)
        lines = [
            "# 회의 리포트",
            "",
            f"- 세션 ID: {refinement_input.session_id}",
            "",
            "## 회의 개요",
            f"- 추출 이벤트: {len(cleaned_events)}건",
            f"- 질문: {len(grouped['question'])}건",
            f"- 결정 사항: {len(grouped['decision'])}건",
            f"- 액션 아이템: {len(grouped['action_item'])}건",
            f"- 리스크: {len(grouped['risk'])}건",
        ]

        self._append_question_section(lines, grouped["question"])
        self._append_decision_section(lines, grouped["decision"])
        self._append_action_item_section(lines, grouped["action_item"])
        self._append_risk_section(lines, grouped["risk"])

        other_events = [
            event
            for event_type, items in grouped.items()
            if event_type not in {"question", "decision", "action_item", "risk"}
            for event in items
        ]
        if other_events:
            self._append_generic_section(lines, "기타 이벤트", other_events)

        self._append_speaker_notes(lines, refinement_input.speaker_transcript_lines)
        self._append_speaker_events(
            lines,
            self._clean_speaker_event_lines(refinement_input.speaker_event_lines),
        )
        return "\n".join(lines)

    @classmethod
    def _clean_events(
        cls,
        events: list[ReportRefinementEvent],
    ) -> list[ReportRefinementEvent]:
        deduped_by_evidence: dict[tuple[str, str], ReportRefinementEvent] = {}
        ordered_events: list[ReportRefinementEvent] = []

        for event in events:
            if cls._is_meta_event(event):
                continue

            evidence_key = cls._normalize_key(event.evidence_text or event.title)
            if evidence_key:
                dedupe_key = (event.event_type, evidence_key)
                existing = deduped_by_evidence.get(dedupe_key)
                if existing is None:
                    deduped_by_evidence[dedupe_key] = event
                    ordered_events.append(event)
                else:
                    deduped_by_evidence[dedupe_key] = cls._pick_better_event(existing, event)
                continue

            ordered_events.append(event)

        result: list[ReportRefinementEvent] = []
        seen_keys: set[tuple[str, str]] = set()
        for event in ordered_events:
            evidence_key = cls._normalize_key(event.evidence_text or event.title)
            if evidence_key:
                dedupe_key = (event.event_type, evidence_key)
                if dedupe_key in seen_keys:
                    continue
                event = deduped_by_evidence[dedupe_key]
                seen_keys.add(dedupe_key)
            result.append(event)
        return result

    @classmethod
    def _clean_speaker_event_lines(cls, lines: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for line in lines:
            normalized = cls._normalize_key(line)
            if not normalized or cls._looks_like_meta_line(line):
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            cleaned.append(line)
        return cleaned

    @classmethod
    def _is_meta_event(cls, event: ReportRefinementEvent) -> bool:
        combined = " ".join(
            part
            for part in (
                cls._normalize_key(event.title),
                cls._normalize_key(event.evidence_text or ""),
            )
            if part
        )
        return any(pattern in combined for pattern in cls._META_PATTERNS)

    @classmethod
    def _looks_like_meta_line(cls, line: str) -> bool:
        normalized = cls._normalize_key(line)
        return any(pattern in normalized for pattern in cls._META_PATTERNS)

    @classmethod
    def _pick_better_event(
        cls,
        current: ReportRefinementEvent,
        candidate: ReportRefinementEvent,
    ) -> ReportRefinementEvent:
        if cls._event_score(candidate) > cls._event_score(current):
            return candidate
        return current

    @classmethod
    def _event_score(cls, event: ReportRefinementEvent) -> tuple[int, int, int]:
        title = event.title.strip()
        question_like = 1 if ("?" in title or "요?" in title or title.endswith("가요")) else 0
        imperative_like = 1 if any(token in title for token in ("정리", "업데이트", "재개", "상향")) else 0
        generic_like = 0 if any(token in title for token in ("확인 필요", "문의")) else 1
        base = question_like if event.event_type == "question" else imperative_like
        return (base, generic_like, -len(title))

    @staticmethod
    def _normalize_key(value: str) -> str:
        collapsed = re.sub(r"\s+", "", value).lower()
        return re.sub(r"[^\w가-힣]", "", collapsed)

    @staticmethod
    def _group_events(
        events: list[ReportRefinementEvent],
    ) -> dict[str, list[ReportRefinementEvent]]:
        grouped: dict[str, list[ReportRefinementEvent]] = defaultdict(list)
        for event in events:
            grouped[event.event_type].append(event)
        return grouped

    def _append_question_section(
        self,
        lines: list[str],
        events: list[ReportRefinementEvent],
    ) -> None:
        lines.extend(["", "## 질문"])
        if not events:
            lines.append("- 없음")
            return
        for event in events:
            lines.append(f"- {event.title}")
            lines.extend(self._build_metadata_lines(event))

    def _append_decision_section(
        self,
        lines: list[str],
        events: list[ReportRefinementEvent],
    ) -> None:
        lines.extend(["", "## 결정 사항"])
        if not events:
            lines.append("- 없음")
            return
        for index, event in enumerate(events, start=1):
            lines.append(f"{index}. {event.title}")
            lines.extend(self._build_metadata_lines(event))

    def _append_action_item_section(
        self,
        lines: list[str],
        events: list[ReportRefinementEvent],
    ) -> None:
        lines.extend(["", "## 액션 아이템"])
        if not events:
            lines.append("- 없음")
            return
        for event in events:
            checkbox = "x" if event.state in {"closed", "resolved"} else " "
            lines.append(f"- [{checkbox}] {event.title}")
            lines.extend(self._build_metadata_lines(event))

    def _append_risk_section(
        self,
        lines: list[str],
        events: list[ReportRefinementEvent],
    ) -> None:
        lines.extend(["", "## 리스크"])
        if not events:
            lines.append("- 없음")
            return
        for event in events:
            lines.append(f"- {event.title}")
            lines.extend(self._build_metadata_lines(event))

    def _append_generic_section(
        self,
        lines: list[str],
        heading: str,
        events: list[ReportRefinementEvent],
    ) -> None:
        lines.extend(["", f"## {heading}"])
        if not events:
            lines.append("- 없음")
            return
        for event in events:
            lines.append(f"- [{event.event_type}] {event.title}")
            lines.extend(self._build_metadata_lines(event))

    def _append_speaker_notes(
        self,
        lines: list[str],
        speaker_transcript_lines: list[str],
    ) -> None:
        lines.extend(["", "## 참고 전사"])
        if not speaker_transcript_lines:
            lines.append("- 없음")
            return
        for line in speaker_transcript_lines:
            lines.append(f"- {line}")

    def _append_speaker_events(
        self,
        lines: list[str],
        speaker_event_lines: list[str],
    ) -> None:
        lines.extend(["", "## 발화자 기반 인사이트"])
        if not speaker_event_lines:
            lines.append("- 없음")
            return
        for line in speaker_event_lines:
            lines.append(f"- {line}")

    @staticmethod
    def _build_metadata_lines(event: ReportRefinementEvent) -> list[str]:
        metadata_lines: list[str] = []
        if event.evidence_text:
            metadata_lines.append(f"  - 근거: {event.evidence_text}")
        return metadata_lines
