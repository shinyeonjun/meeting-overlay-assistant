"""STT 전사를 회의록 정본 섹션으로 분석하는 서비스."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, replace
from typing import Any

from server.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)
from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)
from server.app.services.reports.composition.report_document import (
    ReportActionItem,
    ReportDocumentV1,
    ReportListItem,
    ReportSection,
)
from server.app.services.reports.composition.report_document_mapper import (
    ReportSessionContext,
)
from server.app.services.reports.composition.timeline_format import (
    format_timeline_range,
)


logger = logging.getLogger(__name__)

_LIST_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
    },
    "required": ["text"],
    "additionalProperties": False,
}

_ACTION_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "task": {"type": "string"},
        "owner": {"type": ["string", "null"]},
        "due_date": {"type": ["string", "null"]},
        "status": {"type": ["string", "null"]},
        "note": {"type": ["string", "null"]},
    },
    "required": ["task", "owner", "due_date", "status", "note"],
    "additionalProperties": False,
}

_SECTION_ITEM_SCHEMA: dict[str, Any] = {
    "type": "array",
    "items": {"type": "string"},
}

_SECTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "time_range": {"type": ["string", "null"]},
        "background": _SECTION_ITEM_SCHEMA,
        "opinions": _SECTION_ITEM_SCHEMA,
        "review": _SECTION_ITEM_SCHEMA,
        "direction": _SECTION_ITEM_SCHEMA,
    },
    "required": ["title", "time_range", "background", "opinions", "review", "direction"],
    "additionalProperties": False,
}

_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "agenda": {
            "type": "string",
        },
        "overview": {
            "type": "array",
            "items": {"type": "string"},
        },
        "sections": {
            "type": "array",
            "items": _SECTION_SCHEMA,
        },
        "special_notes": {
            "type": "array",
            "items": _LIST_ITEM_SCHEMA,
        },
        "decisions": {
            "type": "array",
            "items": _LIST_ITEM_SCHEMA,
        },
        "follow_up": {
            "type": "array",
            "items": _ACTION_ITEM_SCHEMA,
        },
    },
    "required": [
        "agenda",
        "overview",
        "sections",
        "decisions",
        "special_notes",
        "follow_up",
    ],
    "additionalProperties": False,
}

_SYSTEM_PROMPT = """
너는 한국어 회의록 작성자다.

작성 원칙:
- 회의록은 전사 요약본이 아니라 안건 중심 문서로 작성한다.
- 제공된 STT 전사와 이벤트 후보에 근거한 내용만 작성한다.
- STT 원문을 그대로 옮기지 말고, 발화의 말투와 군더더기를 제거해 회의록 문장으로 재구성한다.
- SPEAKER_00, SPEAKER_01 같은 시스템 화자 라벨은 최종 문장에 절대 쓰지 않는다.
- "생각합니다", "나왔습니다", "단어 사용", 괄호 설명처럼 전사 분석 흔적이 남는 표현은 쓰지 않는다.
- 회의록 문장은 "~을 논의함", "~을 검토함", "~으로 정리함"처럼 간결한 공식 문서체로 쓴다.
- 여러 발화를 하나의 논의 주제로 묶어 정리한다.
- 짧은 감탄, 되묻기, 농담, 의미 없는 맞장구는 제외한다.
- 추측으로 결정사항, 담당자, 날짜, 상태를 만들지 않는다.
- 담당자, 날짜, 상태를 알 수 없으면 빈 문자열이나 null로 둔다.
- 해당 필드에 넣을 근거가 없으면 빈 배열로 둔다.
- 사용자에게 공유되는 회의록에 근거 구간, 발화자, 원문 인용을 노출하지 않는다.

출력 구조:
- agenda: 회의개요의 안건 칸에 들어갈 회의 전체 주제 1개만 작성한다.
- overview: 회의 전체를 빠르게 이해할 수 있는 핵심 요약을 작성한다.
- sections: 먼저 STT 전체에서 회의내용 소주제를 식별한 뒤, 소주제별로 관련 발화를 묶어 작성한다.
- sections.title: 회의내용 안에서 사용할 소주제명만 짧게 적는다.
- sections.background: 해당 소주제가 왜 논의되었는지 배경을 적는다.
- sections.opinions: 참석자들이 낸 주요 의견을 회의록 문장으로 정리한다.
- sections.review: 비교, 검토, 우려, 확인 필요 내용을 정리한다.
- sections.direction: 논의 결과 정리된 방향을 적는다.
- decisions: 회의에서 합의되었거나 확정된 결정사항만 적는다.
- special_notes: 결정이나 할 일은 아니지만 회의록에 남길 필요가 있는 리스크, 주의사항, 미확정 이슈, 확인 필요 사항을 적는다.
- follow_up: 회의 후 실제로 해야 할 일만 적는다.

필드별 작성 기준:
- agenda는 회의 전체를 대표하는 주제 한 줄이어야 하며, 20~60자 정도로 작성한다.
- agenda에는 여러 논의 항목을 나열하지 않는다.
- agenda에는 "회의내용 요약", "정리", "논의"처럼 모호한 표현만 쓰지 않는다.
- 하나의 sections 항목은 제목, 논의 배경, 주요 의견, 검토 내용, 정리된 방향이 계층을 이루어야 한다.
- sections.title에는 세부 내용을 반복해서 쓰지 말고, 주제명만 쓴다.
- background, opinions, review, direction에는 title을 그대로 반복하지 않는다.
- 질문 문장, 감탄, 농담, 맞장구를 그대로 넣지 말고 논의된 쟁점과 검토 결과로 바꿔 쓴다.
- 특정 소주제에서 해당 필드의 근거가 없으면 그 필드만 빈 배열로 둔다.
- "SPEAKER_01: 비주얼적인 측면을 더 신경써야 한다고 생각합니다."처럼 쓰지 말고, "비주얼 요소 개선 필요성이 제기됨"처럼 재작성한다.
- "(비주얼이라는 단어 사용)"처럼 특정 단어가 쓰였다는 메타 설명은 쓰지 않는다.
- 회의내용에 쓸 실질 논의가 있으면 sections는 최소 1개 이상 작성한다.
- decisions에는 단순 의견, 아이디어, 질문, 할 일을 넣지 않는다. 최종 합의와 확정 사항만 넣는다.
- "의견이 모아졌습니다"처럼 합의 여부가 불명확한 표현은 decisions에 넣지 말고 sections에 넣는다.
- special_notes에는 sections에 이미 적은 일반 논의를 다시 넣지 않는다. 회의록에 별도로 남겨야 할 주의사항만 넣는다.
- special_notes는 반복 요약이나 중요 주제 목록이 아니다. 별도 리스크, 주의사항, 미확정 이슈가 없으면 빈 배열로 둔다.
- follow_up에는 sections나 special_notes에 적은 미확정 논의를 할 일처럼 바꾸어 넣지 않는다.
- 같은 내용을 sections, decisions, special_notes, follow_up에 반복해서 넣지 않는다.

분량 기준:
- 개수는 고정하지 않는다.
- 실제 회의에서 중요하게 다뤄진 내용은 필요한 만큼 작성한다.
- 다만 같은 내용을 쪼개서 여러 항목으로 늘리거나, 잡담/반응/중복 내용을 채우지 않는다.
- special_notes와 follow_up은 실제 근거가 있을 때만 작성한다.
- 응답은 반드시 JSON 하나만 반환한다.
""".strip()


@dataclass(frozen=True)
class MeetingMinutesAnalyzerConfig:
    """회의록 AI 분석 설정."""

    model: str
    max_transcript_chars: int = 8_000
    max_event_candidates: int = 12
    map_reduce_segment_threshold: int = 36
    max_segments_per_chunk: int = 20
    keep_alive: str | None = "30m"
    use_response_schema: bool = True


@dataclass(frozen=True)
class _AnalyzedSection:
    title: str
    time_range: str | None
    background: tuple[ReportListItem, ...]
    opinions: tuple[ReportListItem, ...]
    review: tuple[ReportListItem, ...]
    direction: tuple[ReportListItem, ...]


class NoOpMeetingMinutesAnalyzer:
    """회의록 AI 분석을 비활성화한다."""

    def analyze(
        self,
        *,
        session_id: str,
        session_context: ReportSessionContext | None,
        speaker_transcript: list[SpeakerTranscriptSegment],
        events: list,
        fallback_document: ReportDocumentV1,
    ) -> ReportDocumentV1 | None:
        del session_id, session_context, speaker_transcript, events, fallback_document
        return None


class LLMMeetingMinutesAnalyzer:
    """교정된 STT 전체를 LLM에 보내 공유용 회의록 섹션을 만든다."""

    def __init__(
        self,
        completion_client: LLMCompletionClient,
        *,
        config: MeetingMinutesAnalyzerConfig,
    ) -> None:
        self._completion_client = completion_client
        self._config = config

    def analyze(
        self,
        *,
        session_id: str,
        session_context: ReportSessionContext | None,
        speaker_transcript: list[SpeakerTranscriptSegment],
        events: list,
        fallback_document: ReportDocumentV1,
    ) -> ReportDocumentV1 | None:
        """LLM 분석이 성공하면 fallback 문서 위에 회의록 섹션을 덮어쓴다."""

        if not speaker_transcript:
            return None

        payload = self._analyze_payload(
            session_id=session_id,
            session_context=session_context,
            speaker_transcript=speaker_transcript,
            events=events,
        )
        if payload is None:
            return None

        overview = _parse_overview(payload.get("overview"))
        agenda = _parse_agenda(payload.get("agenda"))
        sections = _parse_sections(payload.get("sections"))
        report_sections = _build_report_sections(sections)
        discussion = _build_discussion_from_sections(sections)
        decisions = _parse_list_items(payload.get("decisions"))
        special_notes = _parse_list_items(payload.get("special_notes"))
        follow_up = _parse_action_items(payload.get("follow_up"))

        if not any((overview, agenda, discussion, decisions, special_notes, follow_up)):
            return None

        return replace(
            fallback_document,
            summary=tuple(overview) or fallback_document.summary,
            sections=tuple(report_sections),
            agenda=tuple(agenda) or fallback_document.agenda,
            discussion=tuple(discussion),
            decisions=tuple(decisions) or fallback_document.decisions,
            risks=tuple(special_notes) or fallback_document.risks,
            action_items=tuple(follow_up) or fallback_document.action_items,
        )

    def _analyze_payload(
        self,
        *,
        session_id: str,
        session_context: ReportSessionContext | None,
        speaker_transcript: list[SpeakerTranscriptSegment],
        events: list,
    ) -> dict[str, object] | None:
        if self._should_use_chunked_analysis(speaker_transcript):
            return self._analyze_payload_in_chunks(
                session_id=session_id,
                session_context=session_context,
                speaker_transcript=speaker_transcript,
                events=events,
            )

        prompt = self._build_prompt(
            session_id=session_id,
            session_context=session_context,
            speaker_transcript=speaker_transcript,
            events=events,
        )
        return self._complete_json_payload(
            session_id=session_id,
            prompt=prompt,
            stage="single",
            transcript_segments=len(speaker_transcript),
        )

    def _should_use_chunked_analysis(
        self,
        speaker_transcript: list[SpeakerTranscriptSegment],
    ) -> bool:
        threshold = max(self._config.map_reduce_segment_threshold, 1)
        max_segments = max(self._config.max_segments_per_chunk, 1)
        return len(speaker_transcript) > threshold and len(speaker_transcript) > max_segments

    def _analyze_payload_in_chunks(
        self,
        *,
        session_id: str,
        session_context: ReportSessionContext | None,
        speaker_transcript: list[SpeakerTranscriptSegment],
        events: list,
    ) -> dict[str, object] | None:
        chunks = _chunk_segments(
            speaker_transcript,
            max_segments=max(self._config.max_segments_per_chunk, 1),
        )
        logger.info(
            "회의록 AI 분할 분석 시작: session_id=%s model=%s transcript_segments=%s chunks=%s chunk_size=%s",
            session_id,
            self._config.model,
            len(speaker_transcript),
            len(chunks),
            max(self._config.max_segments_per_chunk, 1),
        )

        payloads: list[dict[str, object]] = []
        for index, chunk in enumerate(chunks, start=1):
            prompt = self._build_prompt(
                session_id=session_id,
                session_context=session_context,
                speaker_transcript=chunk,
                events=events,
                analysis_scope=f"chunk {index}/{len(chunks)}",
            )
            payload = self._complete_json_payload(
                session_id=session_id,
                prompt=prompt,
                stage=f"chunk {index}/{len(chunks)}",
                transcript_segments=len(chunk),
            )
            if payload is not None:
                payloads.append(payload)

        if not payloads:
            logger.warning(
                "회의록 AI 분할 분석 결과 없음: session_id=%s model=%s chunks=%s",
                session_id,
                self._config.model,
                len(chunks),
            )
            return None

        logger.info(
            "회의록 AI 분할 분석 병합: session_id=%s model=%s success_chunks=%s total_chunks=%s",
            session_id,
            self._config.model,
            len(payloads),
            len(chunks),
        )
        return _merge_chunk_payloads(payloads)

    def _complete_json_payload(
        self,
        *,
        session_id: str,
        prompt: str,
        stage: str,
        transcript_segments: int,
    ) -> dict[str, object] | None:
        started_at = time.perf_counter()
        logger.info(
            "회의록 AI 분석 시작: session_id=%s model=%s stage=%s prompt_chars=%s transcript_segments=%s",
            session_id,
            self._config.model,
            stage,
            len(prompt),
            transcript_segments,
        )
        try:
            response_text = self._completion_client.complete(
                prompt,
                system_prompt=_SYSTEM_PROMPT,
                response_schema=(
                    _RESPONSE_SCHEMA if self._config.use_response_schema else None
                ),
                keep_alive=self._config.keep_alive,
            )
            payload = _load_json_response(response_text)
        except Exception:
            logger.exception(
                "회의록 AI 분석 실패: session_id=%s model=%s stage=%s prompt_chars=%s elapsed=%.2fs",
                session_id,
                self._config.model,
                stage,
                len(prompt),
                time.perf_counter() - started_at,
            )
            return None
        logger.info(
            "회의록 AI 분석 완료: session_id=%s model=%s stage=%s elapsed=%.2fs response_chars=%s",
            session_id,
            self._config.model,
            stage,
            time.perf_counter() - started_at,
            len(response_text),
        )
        return payload

    def _build_prompt(
        self,
        *,
        session_id: str,
        session_context: ReportSessionContext | None,
        speaker_transcript: list[SpeakerTranscriptSegment],
        events: list,
        analysis_scope: str = "full",
    ) -> str:
        payload = {
            "session_id": session_id,
            "analysis_scope": analysis_scope,
            "회의 메타데이터": _build_context_payload(session_context),
            "작성할 필드": [
                "agenda",
                "overview",
                "sections.title",
                "sections.background",
                "sections.opinions",
                "sections.review",
                "sections.direction",
                "decisions",
                "special_notes",
                "follow_up",
            ],
            "이벤트 후보": _build_event_candidates(
                events,
                limit=self._config.max_event_candidates,
            ),
            "STT 전사": self._build_transcript_payload(speaker_transcript),
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def _build_transcript_payload(
        self,
        speaker_transcript: list[SpeakerTranscriptSegment],
    ) -> list[dict[str, object]]:
        entries: list[dict[str, object]] = []
        total_chars = 0
        for segment in speaker_transcript:
            text = _clean_text(segment.text)
            if not text:
                continue
            entry = {
                "time_range": format_timeline_range(segment.start_ms, segment.end_ms),
                "speaker": segment.speaker_label,
                "text": text,
            }
            total_chars += len(text)
            if entries and total_chars > self._config.max_transcript_chars:
                entries.append(
                    {
                        "time_range": "-",
                        "speaker": "system",
                        "text": "전사가 길어 이후 일부 구간은 이번 AI 분석 입력에서 생략되었습니다.",
                    }
                )
                break
            entries.append(entry)
        return entries


def _build_context_payload(
    session_context: ReportSessionContext | None,
) -> dict[str, object]:
    if session_context is None:
        return {}
    return {
        "title": session_context.title,
        "started_at": session_context.started_at,
        "ended_at": session_context.ended_at,
        "participants": list(session_context.participants),
        "organizer": session_context.organizer,
        "primary_input_source": session_context.primary_input_source,
    }


def _build_event_candidates(events: list, *, limit: int) -> list[dict[str, object]]:
    candidates = []
    for event in events[:limit]:
        candidates.append(
            {
                "event_type": _value_of(getattr(event, "event_type", "")),
                "title": getattr(event, "title", ""),
                "state": _value_of(getattr(event, "state", "")),
                "speaker": getattr(event, "speaker_label", None),
                "evidence": getattr(event, "evidence_text", None),
            }
        )
    return candidates


def _chunk_segments(
    speaker_transcript: list[SpeakerTranscriptSegment],
    *,
    max_segments: int,
) -> list[list[SpeakerTranscriptSegment]]:
    chunks: list[list[SpeakerTranscriptSegment]] = []
    current: list[SpeakerTranscriptSegment] = []
    for segment in speaker_transcript:
        if len(current) >= max_segments:
            chunks.append(current)
            current = []
        current.append(segment)
    if current:
        chunks.append(current)
    return chunks


def _merge_chunk_payloads(payloads: list[dict[str, object]]) -> dict[str, object]:
    return {
        "agenda": _merge_agenda(payloads),
        "overview": _merge_string_arrays(payloads, "overview", limit=6),
        "sections": _merge_sections(payloads),
        "decisions": _merge_object_list_items(payloads, "decisions", limit=8),
        "special_notes": _merge_object_list_items(payloads, "special_notes", limit=8),
        "follow_up": _merge_action_items(payloads, limit=8),
    }


def _merge_agenda(payloads: list[dict[str, object]]) -> str:
    for payload in payloads:
        agenda = _clean_text(payload.get("agenda"))
        if agenda:
            return _limit_text(agenda, 80) or agenda
    section_titles = [
        _clean_text(section.get("title"))
        for payload in payloads
        for section in _iter_raw_sections(payload.get("sections"))
    ]
    if section_titles:
        return " / ".join(_dedupe_strings(section_titles, limit=3))
    return ""


def _merge_sections(payloads: list[dict[str, object]]) -> list[dict[str, object]]:
    merged_by_key: dict[str, dict[str, object]] = {}
    ordered_keys: list[str] = []
    for payload in payloads:
        for section in _iter_raw_sections(payload.get("sections")):
            title = _clean_text(section.get("title"))
            if not title:
                continue
            key = _normalize_merge_key(title)
            if key not in merged_by_key:
                merged_by_key[key] = {
                    "title": _limit_text(title, 120) or title,
                    "time_range": _normalize_optional(section.get("time_range")),
                    "background": [],
                    "opinions": [],
                    "review": [],
                    "direction": [],
                }
                ordered_keys.append(key)
            target = merged_by_key[key]
            if target.get("time_range") is None:
                target["time_range"] = _normalize_optional(section.get("time_range"))
            for field in ("background", "opinions", "review", "direction"):
                target[field] = _dedupe_strings(
                    [*target[field], *_extract_string_items(section.get(field))],
                    limit=5,
                )

    return [merged_by_key[key] for key in ordered_keys[:8]]


def _merge_string_arrays(
    payloads: list[dict[str, object]],
    key: str,
    *,
    limit: int,
) -> list[str]:
    items: list[str] = []
    for payload in payloads:
        items.extend(_extract_string_items(payload.get(key)))
    return _dedupe_strings(items, limit=limit)


def _merge_object_list_items(
    payloads: list[dict[str, object]],
    key: str,
    *,
    limit: int,
) -> list[dict[str, str]]:
    texts: list[str] = []
    for payload in payloads:
        for raw_item in _iter_raw_list(payload.get(key)):
            if isinstance(raw_item, dict):
                texts.append(_clean_text(raw_item.get("text")))
            else:
                texts.append(_clean_text(raw_item))
    return [{"text": text} for text in _dedupe_strings(texts, limit=limit)]


def _merge_action_items(
    payloads: list[dict[str, object]],
    *,
    limit: int,
) -> list[dict[str, str | None]]:
    items: list[dict[str, str | None]] = []
    seen: set[str] = set()
    for payload in payloads:
        for raw_item in _iter_raw_list(payload.get("follow_up")):
            if not isinstance(raw_item, dict):
                continue
            task = _clean_text(raw_item.get("task"))
            if not task:
                continue
            key = _normalize_merge_key(task)
            if key in seen:
                continue
            seen.add(key)
            items.append(
                {
                    "task": _limit_text(task, 180),
                    "owner": _normalize_owner(raw_item.get("owner")),
                    "due_date": _normalize_optional(raw_item.get("due_date")),
                    "status": _normalize_status(raw_item.get("status")),
                    "note": _limit_text(_clean_text(raw_item.get("note")), 180),
                }
            )
            if len(items) >= limit:
                return items
    return items


def _iter_raw_sections(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _iter_raw_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _extract_string_items(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_clean_text(item) for item in value if _clean_text(item)]


def _dedupe_strings(items: list[str], *, limit: int) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        cleaned = _limit_text(_clean_text(item), 220)
        if not cleaned:
            continue
        key = _normalize_merge_key(cleaned)
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
        if len(result) >= limit:
            break
    return result


def _normalize_merge_key(value: str) -> str:
    return "".join(_clean_text(value).lower().split())


def _load_json_response(response_text: str) -> dict[str, object]:
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError:
        payload = json.loads(_extract_json_object(response_text))
    if not isinstance(payload, dict):
        raise ValueError("회의록 AI 응답은 JSON object여야 합니다.")
    return payload


def _extract_json_object(response_text: str) -> str:
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise json.JSONDecodeError("JSON object를 찾을 수 없습니다.", response_text, 0)
    return cleaned[start : end + 1]


def _parse_list_items(value: object) -> list[ReportListItem]:
    if not isinstance(value, list):
        return []
    items: list[ReportListItem] = []
    for raw_item in value:
        if isinstance(raw_item, str):
            text = _clean_text(raw_item)
            if text:
                items.append(ReportListItem(text=_limit_text(text, 220) or text))
            continue
        if not isinstance(raw_item, dict):
            continue
        text = _clean_text(raw_item.get("text"))
        if not text:
            continue
        items.append(
            ReportListItem(
                text=_limit_text(text, 220),
                evidence=_limit_text(_clean_text(raw_item.get("evidence")), 180),
                time_range=_normalize_optional(raw_item.get("time_range")),
            )
        )
    return items


def _parse_overview(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    overview: list[str] = []
    for raw_item in value:
        text = _clean_text(raw_item)
        if text:
            overview.append(_limit_text(text, 220) or "")
    return overview


def _parse_agenda(value: object) -> list[ReportListItem]:
    text = _clean_text(value)
    if not text:
        return []
    return [ReportListItem(text=text)]


def _parse_section_text_items(value: object) -> tuple[ReportListItem, ...]:
    if not isinstance(value, list):
        return ()
    items: list[ReportListItem] = []
    for raw_item in value:
        text = _clean_text(raw_item)
        if text:
            items.append(ReportListItem(text=_limit_text(text, 220) or text))
    return tuple(items)


def _parse_sections(value: object) -> list[_AnalyzedSection]:
    if not isinstance(value, list):
        return []
    sections: list[_AnalyzedSection] = []
    for raw_section in value:
        if not isinstance(raw_section, dict):
            continue
        title = _clean_text(raw_section.get("title"))
        if not title:
            continue
        sections.append(
            _AnalyzedSection(
                title=_limit_text(title, 120) or title,
                time_range=_normalize_optional(raw_section.get("time_range")),
                background=_parse_section_text_items(raw_section.get("background")),
                opinions=_parse_section_text_items(raw_section.get("opinions")),
                review=_parse_section_text_items(raw_section.get("review")),
                direction=_parse_section_text_items(raw_section.get("direction")),
            )
        )
    return sections


def _build_report_sections(
    sections: list[_AnalyzedSection],
) -> list[ReportSection]:
    return [
        ReportSection(
            title=section.title,
            time_range=section.time_range,
            background=section.background,
            opinions=section.opinions,
            review=section.review,
            direction=section.direction,
        )
        for section in sections
    ]


def _build_discussion_from_sections(
    sections: list[_AnalyzedSection],
) -> list[ReportListItem]:
    discussion: list[ReportListItem] = []
    for section in sections:
        discussion.extend(section.background)
        discussion.extend(section.opinions)
        discussion.extend(section.review)
        discussion.extend(section.direction)
    return discussion


def _parse_action_items(value: object) -> list[ReportActionItem]:
    if not isinstance(value, list):
        return []
    items: list[ReportActionItem] = []
    for raw_item in value:
        if not isinstance(raw_item, dict):
            continue
        task = _clean_text(raw_item.get("task"))
        if not task:
            continue
        items.append(
            ReportActionItem(
                task=_limit_text(task, 180),
                owner=_normalize_owner(raw_item.get("owner")) or "",
                due_date=_normalize_optional(raw_item.get("due_date")) or "",
                status=_normalize_status(raw_item.get("status")) or "",
                note=_limit_text(_clean_text(raw_item.get("note")), 180),
            )
        )
    return items


def _normalize_optional(value: object) -> str | None:
    cleaned = _clean_text(value)
    if not cleaned or cleaned in {"-", "없음", "미기록", "null", "None", "open", "pending", "대기", "미정"}:
        return None
    return cleaned


def _normalize_owner(value: object) -> str | None:
    owner = _normalize_optional(value)
    if not owner or owner.upper().startswith("SPEAKER_"):
        return None
    return owner


def _normalize_status(value: object) -> str | None:
    status = _normalize_optional(value)
    if not status:
        return None
    status_by_value = {
        "done": "완료",
        "completed": "완료",
        "complete": "완료",
        "resolved": "완료",
        "in_progress": "진행 중",
        "progress": "진행 중",
    }
    return status_by_value.get(status.lower(), status)


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").split())


def _limit_text(value: str | None, limit: int) -> str | None:
    if not value:
        return None
    if len(value) <= limit:
        return value
    return f"{value[: limit - 1].rstrip()}…"


def _value_of(value: object) -> str:
    return str(getattr(value, "value", value))
