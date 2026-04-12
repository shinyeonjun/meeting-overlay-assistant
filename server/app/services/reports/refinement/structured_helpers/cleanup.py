"""리포트 영역의 cleanup 서비스를 제공한다."""
from __future__ import annotations

from collections import defaultdict
import re

from server.app.services.reports.refinement.report_refiner import ReportRefinementEvent


META_PATTERNS = (
    "질문하나더있습니다",
    "질문하나있습니다",
    "추가리스크도있습니다",
    "추가리스크확인해야",
    "추가질문",
)


def clean_events(events: list[ReportRefinementEvent]) -> list[ReportRefinementEvent]:
    """메타 이벤트와 중복 근거 이벤트를 제거한다."""

    deduped_by_evidence: dict[tuple[str, str], ReportRefinementEvent] = {}
    ordered_events: list[ReportRefinementEvent] = []

    for event in events:
        if is_meta_event(event):
            continue

        evidence_key = normalize_key(event.evidence_text or event.title)
        if evidence_key:
            dedupe_key = (event.event_type, evidence_key)
            existing = deduped_by_evidence.get(dedupe_key)
            if existing is None:
                deduped_by_evidence[dedupe_key] = event
                ordered_events.append(event)
            else:
                deduped_by_evidence[dedupe_key] = pick_better_event(existing, event)
            continue

        ordered_events.append(event)

    result: list[ReportRefinementEvent] = []
    seen_keys: set[tuple[str, str]] = set()
    for event in ordered_events:
        evidence_key = normalize_key(event.evidence_text or event.title)
        if evidence_key:
            dedupe_key = (event.event_type, evidence_key)
            if dedupe_key in seen_keys:
                continue
            event = deduped_by_evidence[dedupe_key]
            seen_keys.add(dedupe_key)
        result.append(event)
    return result


def clean_speaker_event_lines(lines: list[str]) -> list[str]:
    """메타성 문장과 중복 발화자 이벤트를 제거한다."""

    cleaned: list[str] = []
    seen: set[str] = set()
    for line in lines:
        normalized = normalize_key(line)
        if not normalized or looks_like_meta_line(line):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(line)
    return cleaned


def group_events(
    events: list[ReportRefinementEvent],
) -> dict[str, list[ReportRefinementEvent]]:
    """이벤트를 event_type 기준으로 묶는다."""

    grouped: dict[str, list[ReportRefinementEvent]] = defaultdict(list)
    for event in events:
        grouped[event.event_type].append(event)
    return grouped


def is_meta_event(event: ReportRefinementEvent) -> bool:
    """사용자용 리포트에 넣지 않을 메타성 이벤트인지 판별한다."""

    combined = " ".join(
        part
        for part in (
            normalize_key(event.title),
            normalize_key(event.evidence_text or ""),
        )
        if part
    )
    return any(pattern in combined for pattern in META_PATTERNS)


def looks_like_meta_line(line: str) -> bool:
    """발화 라인이 메타성 안내 문장인지 판별한다."""

    normalized = normalize_key(line)
    return any(pattern in normalized for pattern in META_PATTERNS)


def pick_better_event(
    current: ReportRefinementEvent,
    candidate: ReportRefinementEvent,
) -> ReportRefinementEvent:
    """중복 근거 이벤트 중 사용자에게 더 자연스러운 문장을 남긴다."""

    if event_score(candidate) > event_score(current):
        return candidate
    return current


def event_score(event: ReportRefinementEvent) -> tuple[int, int, int]:
    """이벤트 제목의 자연스러움을 기준으로 비교 점수를 계산한다."""

    title = event.title.strip()
    question_like = 1 if ("?" in title or "맞나요" in title) else 0
    imperative_like = 1 if any(token in title for token in ("정리", "업데이트", "개선", "영향")) else 0
    generic_like = 0 if any(token in title for token in ("확인 필요", "문의")) else 1
    base = question_like if event.event_type == "question" else imperative_like
    return (base, generic_like, -len(title))


def normalize_key(value: str) -> str:
    """공백과 기호를 제거한 비교용 키를 만든다."""

    collapsed = re.sub(r"\s+", "", value).lower()
    return re.sub(r"[^\w가-힣]", "", collapsed)
