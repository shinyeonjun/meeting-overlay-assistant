"""구조화된 Markdown 회의록 정제기."""

from __future__ import annotations

from server.app.services.reports.refinement.report_refiner import (
    ReportRefinementInput,
    ReportRefiner,
)
from server.app.services.reports.refinement.structured_helpers import (
    build_structured_report_lines,
    clean_events,
    clean_speaker_event_lines,
    group_events,
)


class StructuredMarkdownReportRefiner(ReportRefiner):
    """이벤트 메타데이터 기반으로 사용자용 회의록을 구성한다."""

    def refine(self, refinement_input: ReportRefinementInput) -> str:
        """구조화된 Markdown 회의록을 생성한다."""

        cleaned_events = clean_events(refinement_input.events)
        grouped_events = group_events(cleaned_events)
        lines = build_structured_report_lines(
            refinement_input=refinement_input,
            cleaned_events=cleaned_events,
            grouped_events=grouped_events,
            cleaned_speaker_event_lines=clean_speaker_event_lines(
                refinement_input.speaker_event_lines,
            ),
        )
        return "\n".join(lines)
