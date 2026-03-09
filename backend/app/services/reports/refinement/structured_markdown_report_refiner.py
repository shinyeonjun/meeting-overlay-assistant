"""구조화된 Markdown 리포트 정제기."""

from __future__ import annotations

from collections import defaultdict

from backend.app.services.reports.refinement.report_refiner import (
    ReportRefinementEvent,
    ReportRefinementInput,
    ReportRefiner,
)


class StructuredMarkdownReportRefiner(ReportRefiner):
    """이벤트 메타데이터를 기반으로 사용자용 리포트를 구성한다."""

    def refine(self, refinement_input: ReportRefinementInput) -> str:
        grouped = self._group_events(refinement_input.events)
        lines = [
            "# 회의 리포트",
            "",
            f"- 세션 ID: {refinement_input.session_id}",
            "",
            "## 회의 개요",
            f"- 추출 이벤트: {len(refinement_input.events)}건",
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
        self._append_speaker_events(lines, refinement_input.speaker_event_lines)
        return "\n".join(lines)

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
            checkbox = "x" if event.state in {"confirmed", "closed", "resolved"} else " "
            assignee_suffix = f" ({event.assignee})" if event.assignee else ""
            lines.append(f"- [{checkbox}] {event.title}{assignee_suffix}")
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
        if event.assignee:
            metadata_lines.append(f"  - 담당자: {event.assignee}")
        if event.due_date:
            metadata_lines.append(f"  - 기한: {event.due_date}")
        if event.evidence_text:
            metadata_lines.append(f"  - 근거: {event.evidence_text}")
        return metadata_lines
