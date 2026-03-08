"""구조화된 Markdown 리포트 정제기."""

from __future__ import annotations

from collections import defaultdict

from backend.app.services.reports.refinement.report_refiner import (
    ReportRefinementEvent,
    ReportRefinementInput,
    ReportRefiner,
)


class StructuredMarkdownReportRefiner(ReportRefiner):
    """이벤트 메타데이터를 바탕으로 읽기 좋은 Markdown 리포트를 재구성한다."""

    def refine(self, refinement_input: ReportRefinementInput) -> str:
        grouped = self._group_events(refinement_input.events)
        lines = [
            f"# Session Report: {refinement_input.session_id}",
            "",
            "## Snapshot",
            f"- Total events: {len(refinement_input.events)}",
            f"- Open questions: {self._count_by_state(grouped['question'], {'open', 'candidate'})}",
            f"- Confirmed decisions: {self._count_by_state(grouped['decision'], {'confirmed'})}",
            f"- Pending action items: {self._count_by_state(grouped['action_item'], {'open', 'candidate', 'active'})}",
            f"- Open risks: {self._count_by_state(grouped['risk'], {'open', 'candidate', 'active'})}",
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
            self._append_generic_section(lines, "Other Events", other_events)

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

    @staticmethod
    def _count_by_state(events: list[ReportRefinementEvent], states: set[str]) -> int:
        return sum(1 for event in events if event.state in states)

    def _append_question_section(
        self,
        lines: list[str],
        events: list[ReportRefinementEvent],
    ) -> None:
        lines.extend(["", "## Questions"])
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
        lines.extend(["", "## Decisions"])
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
        lines.extend(["", "## Action Items"])
        if not events:
            lines.append("- 없음")
            return
        for event in events:
            checkbox = "x" if event.state in {"confirmed", "closed"} else " "
            owner_suffix = f" ({event.assignee})" if event.assignee else ""
            lines.append(f"- [{checkbox}] {event.title}{owner_suffix}")
            lines.extend(self._build_metadata_lines(event))

    def _append_risk_section(
        self,
        lines: list[str],
        events: list[ReportRefinementEvent],
    ) -> None:
        lines.extend(["", "## Risks"])
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

    def _append_speaker_notes(self, lines: list[str], speaker_transcript_lines: list[str]) -> None:
        lines.extend(["", "## Speaker Notes"])
        if not speaker_transcript_lines:
            lines.append("- 없음")
            return
        for line in speaker_transcript_lines:
            lines.append(f"- {line}")

    def _append_speaker_events(self, lines: list[str], speaker_event_lines: list[str]) -> None:
        lines.extend(["", "## Speaker-attributed Events"])
        if not speaker_event_lines:
            lines.append("- 없음")
            return
        for line in speaker_event_lines:
            lines.append(f"- {line}")

    @staticmethod
    def _build_metadata_lines(event: ReportRefinementEvent) -> list[str]:
        metadata_lines = [f"  - state: {event.state}"]
        if event.assignee:
            metadata_lines.append(f"  - assignee: {event.assignee}")
        if event.due_date:
            metadata_lines.append(f"  - due_date: {event.due_date}")
        if event.input_source:
            metadata_lines.append(f"  - input_source: {event.input_source}")
        if event.evidence_text:
            metadata_lines.append(f"  - evidence: {event.evidence_text}")
        return metadata_lines
