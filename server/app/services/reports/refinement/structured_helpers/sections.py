"""리포트 영역의 sections 서비스를 제공한다."""
from __future__ import annotations

from server.app.services.reports.refinement.report_refiner import (
    ReportRefinementEvent,
    ReportRefinementInput,
)


def build_structured_report_lines(
    *,
    refinement_input: ReportRefinementInput,
    cleaned_events: list[ReportRefinementEvent],
    grouped_events: dict[str, list[ReportRefinementEvent]],
    cleaned_speaker_event_lines: list[str],
) -> list[str]:
    """사용자용 구조화 리포트 Markdown 줄 목록을 만든다."""

    lines = [
        "# 회의 리포트",
        "",
        f"- 세션 ID: {refinement_input.session_id}",
        "",
        "## 회의 개요",
        f"- 추출 이벤트: {len(cleaned_events)}건",
        f"- 질문: {len(grouped_events['question'])}건",
        f"- 결정 사항: {len(grouped_events['decision'])}건",
        f"- 액션 아이템: {len(grouped_events['action_item'])}건",
        f"- 리스크: {len(grouped_events['risk'])}건",
    ]

    append_question_section(lines, grouped_events["question"])
    append_decision_section(lines, grouped_events["decision"])
    append_action_item_section(lines, grouped_events["action_item"])
    append_risk_section(lines, grouped_events["risk"])

    other_events = [
        event
        for event_type, items in grouped_events.items()
        if event_type not in {"question", "decision", "action_item", "risk"}
        for event in items
    ]
    if other_events:
        append_generic_section(lines, "기타 이벤트", other_events)

    append_speaker_notes(lines, refinement_input.speaker_transcript_lines)
    append_speaker_events(lines, cleaned_speaker_event_lines)
    return lines


def append_question_section(
    lines: list[str],
    events: list[ReportRefinementEvent],
) -> None:
    """질문 섹션을 추가한다."""

    lines.extend(["", "## 질문"])
    if not events:
        lines.append("- 없음")
        return
    for event in events:
        lines.append(f"- {event.title}")
        lines.extend(build_metadata_lines(event))


def append_decision_section(
    lines: list[str],
    events: list[ReportRefinementEvent],
) -> None:
    """결정 사항 섹션을 추가한다."""

    lines.extend(["", "## 결정 사항"])
    if not events:
        lines.append("- 없음")
        return
    for index, event in enumerate(events, start=1):
        lines.append(f"{index}. {event.title}")
        lines.extend(build_metadata_lines(event))


def append_action_item_section(
    lines: list[str],
    events: list[ReportRefinementEvent],
) -> None:
    """액션 아이템 섹션을 추가한다."""

    lines.extend(["", "## 액션 아이템"])
    if not events:
        lines.append("- 없음")
        return
    for event in events:
        checkbox = "x" if event.state in {"closed", "resolved"} else " "
        lines.append(f"- [{checkbox}] {event.title}")
        lines.extend(build_metadata_lines(event))


def append_risk_section(
    lines: list[str],
    events: list[ReportRefinementEvent],
) -> None:
    """리스크 섹션을 추가한다."""

    lines.extend(["", "## 리스크"])
    if not events:
        lines.append("- 없음")
        return
    for event in events:
        lines.append(f"- {event.title}")
        lines.extend(build_metadata_lines(event))


def append_generic_section(
    lines: list[str],
    heading: str,
    events: list[ReportRefinementEvent],
) -> None:
    """기타 이벤트 섹션을 추가한다."""

    lines.extend(["", f"## {heading}"])
    if not events:
        lines.append("- 없음")
        return
    for event in events:
        lines.append(f"- [{event.event_type}] {event.title}")
        lines.extend(build_metadata_lines(event))


def append_speaker_notes(
    lines: list[str],
    speaker_transcript_lines: list[str],
) -> None:
    """참고 전사 섹션을 추가한다."""

    lines.extend(["", "## 참고 전사"])
    if not speaker_transcript_lines:
        lines.append("- 없음")
        return
    for line in speaker_transcript_lines:
        lines.append(f"- {line}")


def append_speaker_events(
    lines: list[str],
    speaker_event_lines: list[str],
) -> None:
    """발화자 기반 인사이트 섹션을 추가한다."""

    lines.extend(["", "## 발화자 기반 인사이트"])
    if not speaker_event_lines:
        lines.append("- 없음")
        return
    for line in speaker_event_lines:
        lines.append(f"- {line}")


def build_metadata_lines(event: ReportRefinementEvent) -> list[str]:
    """이벤트의 부가 메타데이터 줄을 만든다."""

    metadata_lines: list[str] = []
    if event.speaker_label:
        metadata_lines.append(f"  - 발화자: {event.speaker_label}")
    if event.input_source:
        metadata_lines.append(f"  - 입력 소스: {event.input_source}")
    if event.evidence_text:
        metadata_lines.append(f"  - 근거: {event.evidence_text}")
    return metadata_lines
