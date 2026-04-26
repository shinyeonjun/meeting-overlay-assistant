"""워크스페이스 회의 요약용 내부 타입과 정제 유틸."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from server.app.domain.events.meeting_event import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.domain.session import MeetingSession
from server.app.domain.shared.enums import EventType
from server.app.services.sessions.workspace_summary_models import (
    WorkspaceSummaryActionItem,
    WorkspaceSummaryDocument,
    WorkspaceSummaryEvidence,
    WorkspaceSummaryTopic,
)

_MEETING_TYPES = {
    "business_meeting",
    "brainstorming",
    "content",
    "casual",
}


@dataclass(frozen=True)
class _NoteEntry:
    utterance_id: str
    start_ms: int
    end_ms: int
    rendered: str


@dataclass(frozen=True)
class _SummaryInputs:
    headline_seed: str
    note_entries: list[_NoteEntry]
    current_topic: str | None
    topic_candidates: list[dict[str, int | str]]
    decisions: list[dict[str, str | None]]
    next_actions: list[dict[str, str | None]]
    open_questions: list[dict[str, str | None]]


@dataclass(frozen=True)
class _SummaryChunk:
    index: int
    start_ms: int
    end_ms: int
    note_excerpt: str
    topic_candidates: list[dict[str, int | str]]
    decisions: list[dict[str, str | None]]
    next_actions: list[dict[str, str | None]]
    open_questions: list[dict[str, str | None]]


@dataclass(frozen=True)
class _ChunkTopicCandidate:
    title: str
    summary: str


@dataclass(frozen=True)
class _ChunkTopicResult:
    index: int
    start_ms: int
    end_ms: int
    meeting_type_vote: str
    chunk_summary: list[str]
    local_topics: list[_ChunkTopicCandidate]


@dataclass(frozen=True)
class _ReducedTopicSegment:
    source_index: int
    title: str
    summary: str
    start_ms: int
    end_ms: int
    chunk_indexes: list[int]


@dataclass(frozen=True)
class _TopicAnalysisTarget:
    source_index: int
    title: str
    start_ms: int
    end_ms: int
    chunk_indexes: list[int]
    note_excerpt: str
    decisions: list[dict[str, str | None]]
    next_actions: list[dict[str, str | None]]
    open_questions: list[dict[str, str | None]]


@dataclass(frozen=True)
class _TopicAnalysisResult:
    source_index: int
    title: str
    summary: str
    start_ms: int
    end_ms: int
    chunk_indexes: list[int]
    decisions: list[str]
    next_actions: list[WorkspaceSummaryActionItem]
    open_questions: list[str]


def _parse_final_summary_payload(
    *,
    payload: dict[str, object],
    session_id: str,
    source_version: int,
    model: str,
    fallback: WorkspaceSummaryDocument,
    topic_results: list[_TopicAnalysisResult],
    evidence: list[WorkspaceSummaryEvidence],
) -> WorkspaceSummaryDocument:
    headline = str(payload.get("headline") or "").strip() or fallback.headline
    summary = (
        _clean_string_list(payload.get("summary"), limit=4, max_chars=180)
        or fallback.summary
    )
    decisions = (
        _clean_string_list(payload.get("decisions"), limit=3, max_chars=90)
        or fallback.decisions
    )
    next_actions = (
        _clean_action_items(payload.get("next_actions"), limit=3, max_chars=80)
        or fallback.next_actions
    )
    open_questions = (
        _clean_string_list(payload.get("open_questions"), limit=2, max_chars=90)
        or fallback.open_questions
    )
    changed_since_last_meeting = _clean_string_list(
        payload.get("changed_since_last_meeting"),
        limit=2,
        max_chars=90,
    )
    topics = [
        WorkspaceSummaryTopic(
            title=result.title,
            summary=result.summary,
            start_ms=result.start_ms,
            end_ms=result.end_ms,
        )
        for result in topic_results[:4]
    ]
    return WorkspaceSummaryDocument(
        session_id=session_id,
        source_version=source_version,
        model=model,
        headline=headline,
        summary=summary,
        topics=topics or fallback.topics,
        decisions=decisions,
        next_actions=next_actions,
        open_questions=open_questions,
        changed_since_last_meeting=changed_since_last_meeting,
        evidence=evidence or fallback.evidence,
    )


def _parse_chunk_topic_payload(
    *,
    payload: dict[str, object],
    chunk: _SummaryChunk,
    fallback: _ChunkTopicResult,
) -> _ChunkTopicResult:
    meeting_type_vote = _normalize_meeting_type(
        payload.get("meeting_type"),
        fallback.meeting_type_vote,
    )
    chunk_summary = (
        _clean_string_list(payload.get("chunk_summary"), limit=2, max_chars=160)
        or fallback.chunk_summary
    )
    local_topics = _clean_chunk_topics(
        payload.get("local_topics"),
        fallback=fallback.local_topics,
        limit=2,
    )
    return _ChunkTopicResult(
        index=chunk.index,
        start_ms=chunk.start_ms,
        end_ms=chunk.end_ms,
        meeting_type_vote=meeting_type_vote,
        chunk_summary=chunk_summary,
        local_topics=local_topics,
    )


def _parse_topic_timeline_payload(
    *,
    payload: dict[str, object],
    chunks: list[_SummaryChunk],
    fallback_meeting_type: str,
    fallback_topics: list[_ReducedTopicSegment],
) -> tuple[str, list[_ReducedTopicSegment]]:
    meeting_type = _normalize_meeting_type(
        payload.get("meeting_type"),
        fallback_meeting_type,
    )
    raw_topics = payload.get("topics")
    if not isinstance(raw_topics, list):
        return meeting_type, fallback_topics

    topics: list[_ReducedTopicSegment] = []
    seen_chunks: set[tuple[int, ...]] = set()
    for raw_topic in raw_topics:
        if not isinstance(raw_topic, dict):
            continue
        chunk_indexes = _clean_int_list(
            raw_topic.get("chunk_indexes"),
            allowed_values=set(range(len(chunks))),
            limit=8,
        )
        chunk_key = tuple(chunk_indexes)
        if not chunk_indexes or chunk_key in seen_chunks:
            continue
        title = str(raw_topic.get("title") or "").strip()
        summary = str(raw_topic.get("summary") or "").strip()
        if not title or not summary or _looks_like_raw_transcript(summary):
            continue
        start_ms = min(chunks[index].start_ms for index in chunk_indexes)
        end_ms = max(chunks[index].end_ms for index in chunk_indexes)
        topics.append(
            _ReducedTopicSegment(
                source_index=len(topics),
                title=title,
                summary=summary,
                start_ms=start_ms,
                end_ms=end_ms,
                chunk_indexes=chunk_indexes,
            )
        )
        seen_chunks.add(chunk_key)
        if len(topics) >= 5:
            break
    return meeting_type, topics or fallback_topics


def _parse_topic_analysis_payload(
    *,
    payload: dict[str, object],
    target: _TopicAnalysisTarget,
    fallback: _TopicAnalysisResult,
) -> _TopicAnalysisResult:
    summary_text = str(payload.get("summary") or "").strip()
    if not summary_text or _looks_like_raw_transcript(summary_text):
        summary_text = fallback.summary
    return _TopicAnalysisResult(
        source_index=target.source_index,
        title=target.title,
        summary=summary_text,
        start_ms=target.start_ms,
        end_ms=target.end_ms,
        chunk_indexes=target.chunk_indexes,
        decisions=(
            _clean_string_list(payload.get("decisions"), limit=3, max_chars=90)
            or fallback.decisions
        ),
        next_actions=(
            _clean_action_items(payload.get("next_actions"), limit=3, max_chars=80)
            or fallback.next_actions
        ),
        open_questions=(
            _clean_string_list(payload.get("open_questions"), limit=2, max_chars=90)
            or fallback.open_questions
        ),
    )


def _build_fallback_summary(
    *,
    session: MeetingSession,
    source_version: int,
    inputs: _SummaryInputs,
    evidence: list[WorkspaceSummaryEvidence],
    model: str,
) -> WorkspaceSummaryDocument:
    fallback_topics = [
        WorkspaceSummaryTopic(
            title=str(item["title"]),
            summary=f"{item['title']} 관련 논의를 이어갔습니다.",
            start_ms=int(item["start_ms"]),
            end_ms=int(item["end_ms"]),
        )
        for item in inputs.topic_candidates[:4]
    ]

    summary: list[str] = []
    if fallback_topics:
        joined_titles = ", ".join(topic.title for topic in fallback_topics[:3])
        summary.append(f"이번 회의에서는 {joined_titles} 등을 중심으로 논의했습니다.")
    elif inputs.current_topic:
        summary.append(f"이번 회의에서는 {inputs.current_topic}를 중심으로 논의했습니다.")
    if inputs.decisions:
        summary.append(f"정리된 결정 후보로는 {inputs.decisions[0]['title']}가 보입니다.")
    if inputs.next_actions:
        summary.append(f"바로 이어서 할 일 후보로는 {inputs.next_actions[0]['title']}가 있습니다.")
    elif inputs.open_questions:
        summary.append(f"남은 쟁점으로는 {inputs.open_questions[0]['title']}가 있습니다.")
    if not summary:
        summary.append("회의 내용을 바탕으로 핵심 요약을 정리하는 중입니다.")

    return WorkspaceSummaryDocument(
        session_id=session.id,
        source_version=source_version,
        model=model,
        headline=inputs.headline_seed or session.title,
        summary=summary[:4],
        topics=fallback_topics,
        decisions=[item["title"] for item in inputs.decisions[:3]],
        next_actions=[
            WorkspaceSummaryActionItem(
                title=item["title"],
                owner=item["speaker_label"],
            )
            for item in inputs.next_actions[:3]
        ],
        open_questions=[item["title"] for item in inputs.open_questions[:2]],
        changed_since_last_meeting=[],
        evidence=evidence,
    )


def _build_chunk_topic_fallback(chunk: _SummaryChunk) -> _ChunkTopicResult:
    local_topics = [
        _ChunkTopicCandidate(
            title=str(item["title"]),
            summary=f"{item['title']} 관련 대화가 이어졌습니다.",
        )
        for item in chunk.topic_candidates[:2]
    ]
    chunk_summary = (
        [f"{local_topics[0].title} 관련 내용을 확인했습니다."]
        if local_topics
        else ["이 구간에서는 보조 대화나 분위기성 발화가 이어졌습니다."]
    )
    return _ChunkTopicResult(
        index=chunk.index,
        start_ms=chunk.start_ms,
        end_ms=chunk.end_ms,
        meeting_type_vote="business_meeting",
        chunk_summary=chunk_summary,
        local_topics=local_topics,
    )


def _build_fallback_reduced_topics(
    *,
    inputs: _SummaryInputs,
    chunks: list[_SummaryChunk],
) -> list[_ReducedTopicSegment]:
    if inputs.topic_candidates:
        return [
            _ReducedTopicSegment(
                source_index=index,
                title=str(item["title"]),
                summary=f"{item['title']} 관련 논의를 이어갔습니다.",
                start_ms=int(item["start_ms"]),
                end_ms=int(item["end_ms"]),
                chunk_indexes=[
                    chunk.index
                    for chunk in chunks
                    if _ranges_overlap(
                        int(item["start_ms"]),
                        int(item["end_ms"]),
                        chunk.start_ms,
                        chunk.end_ms,
                    )
                ]
                or [0],
            )
            for index, item in enumerate(inputs.topic_candidates[:4])
        ]

    return [
        _ReducedTopicSegment(
            source_index=0,
            title=inputs.current_topic or inputs.headline_seed,
            summary="회의 전체 논의를 한 주제로 정리했습니다.",
            start_ms=chunks[0].start_ms,
            end_ms=chunks[-1].end_ms,
            chunk_indexes=[chunk.index for chunk in chunks],
        )
    ]


def _build_topic_analysis_fallback(target: _TopicAnalysisTarget) -> _TopicAnalysisResult:
    if target.decisions or target.next_actions or target.open_questions:
        summary = f"{target.title} 주제에서 후속 판단이 필요한 논의가 이어졌습니다."
    else:
        summary = f"{target.title} 주제에 대한 논의가 이어졌습니다."
    return _TopicAnalysisResult(
        source_index=target.source_index,
        title=target.title,
        summary=summary,
        start_ms=target.start_ms,
        end_ms=target.end_ms,
        chunk_indexes=target.chunk_indexes,
        decisions=[item["title"] for item in target.decisions[:3]],
        next_actions=[
            WorkspaceSummaryActionItem(
                title=item["title"],
                owner=item["speaker_label"],
            )
            for item in target.next_actions[:3]
        ],
        open_questions=[item["title"] for item in target.open_questions[:2]],
    )


def _build_final_merge_fallback(
    *,
    session: MeetingSession,
    source_version: int,
    inputs: _SummaryInputs,
    meeting_type: str,
    topic_results: list[_TopicAnalysisResult],
    evidence: list[WorkspaceSummaryEvidence],
    model: str,
) -> WorkspaceSummaryDocument:
    del meeting_type
    topics = [
        WorkspaceSummaryTopic(
            title=result.title,
            summary=result.summary,
            start_ms=result.start_ms,
            end_ms=result.end_ms,
        )
        for result in topic_results[:4]
    ]
    summary = _dedupe_strings(
        [result.summary for result in topic_results if result.summary],
        limit=4,
    )
    if not summary:
        joined_titles = ", ".join(topic.title for topic in topics[:3])
        summary = [f"이번 회의에서는 {joined_titles} 등을 중심으로 논의했습니다."]
    return WorkspaceSummaryDocument(
        session_id=session.id,
        source_version=source_version,
        model=model,
        headline=inputs.headline_seed or session.title,
        summary=summary,
        topics=topics,
        decisions=_dedupe_strings(
            [item for result in topic_results for item in result.decisions],
            limit=3,
        ),
        next_actions=_dedupe_action_items(
            [item for result in topic_results for item in result.next_actions],
            limit=3,
        ),
        open_questions=_dedupe_strings(
            [item for result in topic_results for item in result.open_questions],
            limit=2,
        ),
        changed_since_last_meeting=[],
        evidence=evidence,
    )


def _select_event_items(
    events: list[MeetingEvent],
    event_type: EventType | None,
    *,
    limit: int,
    allowed_types: set[EventType] | None = None,
) -> list[dict[str, str | None]]:
    selected: list[dict[str, str | None]] = []
    for event in events:
        if allowed_types is not None:
            if event.event_type not in allowed_types:
                continue
        elif event_type is not None and event.event_type != event_type:
            continue

        title = event.title.strip()
        if not title or _should_skip_event_title(title, event.event_type):
            continue

        selected.append(
            {
                "title": title,
                "speaker_label": event.speaker_label,
                "state": event.state.value if hasattr(event.state, "value") else str(event.state),
            }
        )
        if len(selected) >= limit:
            break
    return selected


def _select_event_items_in_range(
    events: list[MeetingEvent],
    *,
    utterance_by_id: dict[str, Utterance],
    start_ms: int,
    end_ms: int,
    event_type: EventType | None,
    limit: int,
    allowed_types: set[EventType] | None = None,
) -> list[dict[str, str | None]]:
    selected: list[dict[str, str | None]] = []
    for event in events:
        if allowed_types is not None:
            if event.event_type not in allowed_types:
                continue
        elif event_type is not None and event.event_type != event_type:
            continue

        title = event.title.strip()
        if not title or _should_skip_event_title(title, event.event_type):
            continue

        utterance = utterance_by_id.get(event.source_utterance_id or "")
        if utterance is None or not _ranges_overlap(
            start_ms,
            end_ms,
            utterance.start_ms,
            utterance.end_ms,
        ):
            continue

        selected.append(
            {
                "title": title,
                "speaker_label": event.speaker_label,
                "state": event.state.value if hasattr(event.state, "value") else str(event.state),
            }
        )
        if len(selected) >= limit:
            break
    return selected


def _build_evidence(
    *,
    events: list[MeetingEvent],
    utterances: list[Utterance],
) -> list[WorkspaceSummaryEvidence]:
    utterance_by_id = {utterance.id: utterance for utterance in utterances}
    evidence: list[WorkspaceSummaryEvidence] = []
    for event in events:
        if event.event_type not in {
            EventType.DECISION,
            EventType.ACTION_ITEM,
            EventType.QUESTION,
            EventType.RISK,
        }:
            continue
        utterance = utterance_by_id.get(event.source_utterance_id or "")
        if utterance is None:
            continue
        evidence.append(
            WorkspaceSummaryEvidence(
                label=event.title.strip() or "다시 볼 구간",
                start_ms=utterance.start_ms,
                end_ms=utterance.end_ms,
            )
        )
        if len(evidence) >= 3:
            break
    return evidence


def _build_topic_candidates(
    *,
    events: list[MeetingEvent],
    utterances: list[Utterance],
    max_candidates: int = 8,
) -> list[dict[str, int | str]]:
    utterance_by_id = {utterance.id: utterance for utterance in utterances}
    last_utterance_end_ms = max((utterance.end_ms for utterance in utterances), default=0)

    topic_events = [
        event
        for event in events
        if event.event_type == EventType.TOPIC and event.title.strip()
    ]
    if not topic_events:
        return []

    def sort_key(event: MeetingEvent) -> tuple[int, int]:
        utterance = utterance_by_id.get(event.source_utterance_id or "")
        if utterance is not None:
            return (utterance.start_ms, utterance.end_ms)
        return (event.created_at_ms, event.updated_at_ms)

    sorted_events = sorted(topic_events, key=sort_key)
    timeline: list[dict[str, int | str]] = []

    for index, event in enumerate(sorted_events):
        utterance = utterance_by_id.get(event.source_utterance_id or "")
        start_ms = utterance.start_ms if utterance is not None else sort_key(event)[0]
        own_end_ms = utterance.end_ms if utterance is not None else start_ms

        if index + 1 < len(sorted_events):
            next_start_ms = sort_key(sorted_events[index + 1])[0]
            end_ms = max(own_end_ms, next_start_ms - 1)
        else:
            end_ms = max(own_end_ms, last_utterance_end_ms)

        title = event.title.strip()
        if timeline and timeline[-1]["title"] == title:
            timeline[-1]["end_ms"] = max(int(timeline[-1]["end_ms"]), end_ms)
            continue

        timeline.append(
            {
                "source_index": len(timeline),
                "title": title,
                "start_ms": start_ms,
                "end_ms": end_ms,
            }
        )

    return timeline[:max_candidates]


def _select_topic_candidates_for_range(
    topic_candidates: list[dict[str, int | str]],
    *,
    start_ms: int,
    end_ms: int,
) -> list[dict[str, int | str]]:
    selected = [
        item
        for item in topic_candidates
        if _ranges_overlap(
            start_ms,
            end_ms,
            int(item.get("start_ms", 0)),
            int(item.get("end_ms", 0)),
        )
    ]
    return selected[:4] if selected else topic_candidates[:2]


def _clean_string_list(
    raw_value: object,
    *,
    limit: int,
    max_chars: int | None = None,
) -> list[str]:
    if not isinstance(raw_value, list):
        return []

    cleaned: list[str] = []
    for item in raw_value:
        text = str(item or "").strip()
        if not text:
            continue
        if max_chars is not None and len(text) > max_chars:
            continue
        if _looks_like_raw_transcript(text):
            continue
        cleaned.append(text)
        if len(cleaned) >= limit:
            break
    return _dedupe_strings(cleaned, limit=limit)


def _clean_int_list(
    raw_value: object,
    *,
    allowed_values: set[int],
    limit: int,
) -> list[int]:
    if not isinstance(raw_value, list):
        return []
    cleaned: list[int] = []
    for item in raw_value:
        if not isinstance(item, int) or item not in allowed_values:
            continue
        cleaned.append(item)
        if len(cleaned) >= limit:
            break
    return _dedupe_ints(cleaned, limit=limit)


def _clean_action_items(
    raw_value: object,
    *,
    limit: int,
    max_chars: int,
) -> list[WorkspaceSummaryActionItem]:
    if not isinstance(raw_value, list):
        return []

    cleaned: list[WorkspaceSummaryActionItem] = []
    for item in raw_value:
        if isinstance(item, WorkspaceSummaryActionItem):
            title = item.title.strip()
            owner = item.owner
            due_date = item.due_date
        elif isinstance(item, dict):
            title = str(item.get("title") or "").strip()
            owner = (
                str(item.get("owner")).strip()
                if item.get("owner") not in {None, ""}
                else None
            )
            due_date = (
                str(item.get("due_date")).strip()
                if item.get("due_date") not in {None, ""}
                else None
            )
        else:
            continue

        if not title or len(title) > max_chars or _looks_like_raw_transcript(title):
            continue

        cleaned.append(
            WorkspaceSummaryActionItem(
                title=title,
                owner=owner,
                due_date=due_date,
            )
        )
        if len(cleaned) >= limit:
            break
    return _dedupe_action_items(cleaned, limit=limit)


def _clean_chunk_topics(
    raw_value: object,
    *,
    fallback: list[_ChunkTopicCandidate],
    limit: int,
) -> list[_ChunkTopicCandidate]:
    if not isinstance(raw_value, list):
        return fallback

    topics: list[_ChunkTopicCandidate] = []
    seen: set[str] = set()
    for item in raw_value:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        summary = str(item.get("summary") or "").strip()
        normalized = " ".join(title.split()).lower()
        if not title or not summary or normalized in seen:
            continue
        if _looks_like_raw_transcript(title) or _looks_like_raw_transcript(summary):
            continue
        seen.add(normalized)
        topics.append(_ChunkTopicCandidate(title=title, summary=summary))
        if len(topics) >= limit:
            break
    return topics or fallback


def _dedupe_strings(values: list[str], *, limit: int) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        normalized = " ".join(value.split()).lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(value)
        if len(deduped) >= limit:
            break
    return deduped


def _dedupe_ints(values: list[int], *, limit: int) -> list[int]:
    seen: set[int] = set()
    deduped: list[int] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
        if len(deduped) >= limit:
            break
    return deduped


def _dedupe_action_items(
    values: list[WorkspaceSummaryActionItem],
    *,
    limit: int,
) -> list[WorkspaceSummaryActionItem]:
    seen: set[str] = set()
    deduped: list[WorkspaceSummaryActionItem] = []
    for value in values:
        normalized = " ".join(value.title.split()).lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(value)
        if len(deduped) >= limit:
            break
    return deduped


def _reduce_meeting_type(votes: list[str]) -> str:
    normalized_votes = [
        _normalize_meeting_type(value, "business_meeting")
        for value in votes
        if value
    ]
    if not normalized_votes:
        return "business_meeting"
    return Counter(normalized_votes).most_common(1)[0][0]


def _normalize_meeting_type(raw_value: object, fallback: str) -> str:
    value = str(raw_value or "").strip().lower()
    if value in _MEETING_TYPES:
        return value
    return fallback if fallback in _MEETING_TYPES else "business_meeting"


def _should_skip_event_title(title: str, event_type: EventType) -> bool:
    compact = " ".join(title.split())
    if not compact:
        return True
    max_chars_by_type = {
        EventType.TOPIC: 40,
        EventType.DECISION: 80,
        EventType.ACTION_ITEM: 80,
        EventType.QUESTION: 90,
        EventType.RISK: 90,
    }
    if len(compact) > max_chars_by_type.get(event_type, 90):
        return True
    if compact.count(" ") >= 18:
        return True
    return _looks_like_raw_transcript(compact)


def _looks_like_raw_transcript(text: str) -> bool:
    compact = " ".join(text.split())
    if not compact:
        return True
    if len(compact) > 120:
        return True
    if compact.endswith(("?", "??")) and compact.count(" ") >= 8:
        return True
    filler_keywords = (
        "그냥 농담",
        "오버한 거",
        "죄송합니다",
        "아 네",
        "아니요",
        "고맙습니다",
        "감사합니다",
    )
    return any(keyword in compact for keyword in filler_keywords) and compact.count(" ") >= 4


def _ranges_overlap(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
    return start_a <= end_b and start_b <= end_a


def _format_ms(value: int) -> str:
    total_seconds = max(int(value // 1000), 0)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def _format_range(start_ms: int, end_ms: int) -> str:
    return f"{_format_ms(start_ms)} - {_format_ms(end_ms)}"
