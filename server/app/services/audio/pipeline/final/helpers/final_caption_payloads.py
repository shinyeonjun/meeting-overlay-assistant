"""Final caption payload hold/merge helper."""

from __future__ import annotations

import re

from server.app.domain.models.utterance import Utterance
from server.app.services.audio.pipeline.models.live_stream_utterance import (
    LiveStreamUtterance,
)


_FINAL_CAPTION_HOLD_MAX_WAIT_MS = 1_200
_FINAL_CAPTION_HOLD_MAX_COMPACT_LENGTH = 32
_FINAL_CAPTION_MERGE_MAX_COMPACT_LENGTH = 46
_FINAL_CAPTION_MERGE_MAX_GAP_MS = 900
_FINAL_CAPTION_HOLD_MAX_QUEUE_DELAY_MS = 1_500
_FINAL_CAPTION_CONTINUATION_SUFFIX_PATTERN = re.compile(
    r"(?:"
    r"\uC740|\uB294|\uC774|\uAC00|\uC744|\uB97C|"
    r"\uC5D0|\uC5D0\uC11C|\uC640|\uACFC|\uB3C4|\uB9CC|"
    r"\uB85C|\uC73C\uB85C|\uACE0|\uC11C|\uBA70|\uBA74|"
    r"\uB294\uB370|\uC9C0\uB9CC|\uB2C8\uAE4C|\uB77C\uACE0|"
    r"\uCC98\uB7FC|\uBD80\uD130|\uAE4C\uC9C0|\uBC16\uC5D0|"
    r"\uC870\uCC28|\uB9C8\uC800|\uD55C\uD14C|\uC5D0\uAC8C|\uAED8|"
    r"\uB791|\uD558\uACE0"
    r")[\"'”’)]*$"
)
_FINAL_CAPTION_TERMINAL_PATTERN = re.compile(
    r"(?:[.!?…]+|"
    r"합니다|했습니다|됩(?:니다|니까)|입니다|였습니다|"
    r"해요|했어요|돼요|돼요|돼요|돼죠|되죠|"
    r"이에요|예요|네요|군요|죠|지요|"
    r"까요|ㄹ까요|거예요|거죠|같아요|맞아요|"
    r"있어요|없어요|싶어요|좋아요|맞습니다|그렇습니다"
    r")[\"'”’)]*$"
)
_FINAL_CAPTION_NO_SPACE_PREFIXES = (
    "은 ",
    "는 ",
    "이 ",
    "가 ",
    "을 ",
    "를 ",
    "에 ",
    "에서 ",
    "와 ",
    "과 ",
    "도 ",
    "만 ",
    "로 ",
    "으로 ",
    "고 ",
    "서 ",
    "며 ",
    "면 ",
    "는데 ",
    "지만 ",
    "니까 ",
    "라고 ",
    "처럼 ",
    "부터 ",
    "까지 ",
    "밖에 ",
    "조차 ",
    "마저 ",
    "한테 ",
    "에게 ",
    "께 ",
    "랑 ",
    "하고 ",
)


def emit_outgoing_final_caption(
    service,
    *,
    session_id: str,
    saved_utterance: Utterance,
    segment_id: str,
    outgoing_seq_num: int | None,
    alignment_status: str,
    final_queue_delay_ms: int,
    input_source: str | None,
    outgoing_final_utterances,
) -> bool:
    emitted_live_final = service._should_emit_live_final(final_queue_delay_ms)
    final_kind = "archive_final" if emitted_live_final else "late_archive_final"
    outgoing_payload = LiveStreamUtterance.from_utterance(
        saved_utterance,
        segment_id=segment_id,
        seq_num=outgoing_seq_num,
        input_source=input_source,
        kind=final_kind,
        stability=("final" if not emitted_live_final else None),
    )
    outgoing_final_utterances.extend(
        _collect_outgoing_final_caption_payloads(
            service,
            session_id=session_id,
            input_source=input_source,
            payload=outgoing_payload,
            allow_hold=(
                alignment_status == "standalone_final"
                and final_kind == "archive_final"
                and final_queue_delay_ms <= _FINAL_CAPTION_HOLD_MAX_QUEUE_DELAY_MS
            ),
            now_ms=service._now_ms(),
        )
    )
    return emitted_live_final


def drain_ready_final_caption_payloads(
    service,
    *,
    session_id: str,
    input_source: str | None,
    now_ms: int,
    force: bool = False,
) -> list[LiveStreamUtterance]:
    """hold 시간이 지난 final caption payload를 websocket 전송 대상으로 꺼낸다."""

    return service._coordination_state.pop_ready_pending_final_captions(
        now_ms=now_ms,
        session_id=session_id,
        input_source=input_source,
        force=force,
    )


def _collect_outgoing_final_caption_payloads(
    service,
    *,
    session_id: str,
    input_source: str | None,
    payload: LiveStreamUtterance,
    allow_hold: bool,
    now_ms: int,
) -> list[LiveStreamUtterance]:
    pending_entry = service._coordination_state.take_pending_final_caption(
        session_id=session_id,
        input_source=input_source,
    )
    outgoing: list[LiveStreamUtterance] = []
    pending_payload = _payload_from_pending_entry(pending_entry)
    current_payload = payload

    if pending_payload is not None:
        if allow_hold and _should_merge_final_caption_payloads(
            service,
            previous=pending_payload,
            current=current_payload,
        ):
            merged_payload = _merge_final_caption_payloads(
                service,
                previous=pending_payload,
                current=current_payload,
            )
            if _should_hold_final_caption_payload(service, merged_payload):
                _remember_pending_final_caption(
                    service,
                    session_id=session_id,
                    input_source=input_source,
                    payload=merged_payload,
                    now_ms=now_ms,
                )
                return outgoing
            outgoing.append(merged_payload)
            return outgoing
        outgoing.append(pending_payload)

    if allow_hold and _should_hold_final_caption_payload(service, current_payload):
        _remember_pending_final_caption(
            service,
            session_id=session_id,
            input_source=input_source,
            payload=current_payload,
            now_ms=now_ms,
        )
        return outgoing

    outgoing.append(current_payload)
    return outgoing


def _remember_pending_final_caption(
    service,
    *,
    session_id: str,
    input_source: str | None,
    payload: LiveStreamUtterance,
    now_ms: int,
) -> None:
    service._coordination_state.remember_pending_final_caption(
        session_id=session_id,
        input_source=input_source,
        payload=payload,
        hold_until_ms=now_ms + _FINAL_CAPTION_HOLD_MAX_WAIT_MS,
    )


def _payload_from_pending_entry(entry: dict[str, object] | None) -> LiveStreamUtterance | None:
    if not entry:
        return None
    payload = entry.get("payload")
    if isinstance(payload, LiveStreamUtterance):
        return payload
    return None


def _should_hold_final_caption_payload(service, payload: LiveStreamUtterance) -> bool:
    if payload.kind not in {"archive_final", "late_archive_final"}:
        return False
    if _looks_like_terminal_final_caption(payload.text):
        return False
    if not _looks_like_continuation_final_caption(payload.text):
        return False
    return service._compact_length(payload.text) <= _FINAL_CAPTION_HOLD_MAX_COMPACT_LENGTH


def _should_merge_final_caption_payloads(
    service,
    *,
    previous: LiveStreamUtterance,
    current: LiveStreamUtterance,
) -> bool:
    if previous.kind != current.kind:
        return False
    if _looks_like_terminal_final_caption(previous.text):
        return False
    gap_ms = current.start_ms - previous.end_ms
    if gap_ms > _FINAL_CAPTION_MERGE_MAX_GAP_MS:
        return False
    merged_text = _join_final_caption_texts(previous.text, current.text)
    return service._compact_length(merged_text) <= _FINAL_CAPTION_MERGE_MAX_COMPACT_LENGTH


def _merge_final_caption_payloads(
    service,
    *,
    previous: LiveStreamUtterance,
    current: LiveStreamUtterance,
) -> LiveStreamUtterance:
    previous_weight = max(service._compact_length(previous.text), 1)
    current_weight = max(service._compact_length(current.text), 1)
    merged_confidence = (
        (previous.confidence * previous_weight) + (current.confidence * current_weight)
    ) / (previous_weight + current_weight)
    return LiveStreamUtterance.create(
        seq_num=previous.seq_num,
        segment_id=previous.segment_id,
        start_ms=previous.start_ms,
        end_ms=current.end_ms,
        text=_join_final_caption_texts(previous.text, current.text),
        confidence=merged_confidence,
        kind=current.kind,
        revision=None,
        input_source=current.input_source or previous.input_source,
        stability=current.stability or previous.stability,
    )


def _join_final_caption_texts(left: str, right: str) -> str:
    normalized_left = left.strip()
    normalized_right = right.strip()
    if not normalized_left:
        return normalized_right
    if not normalized_right:
        return normalized_left
    if normalized_right[0] in ".,!?)]}\"'":
        return f"{normalized_left}{normalized_right}"
    if any(normalized_right.startswith(prefix) for prefix in _FINAL_CAPTION_NO_SPACE_PREFIXES):
        return f"{normalized_left}{normalized_right}"
    return f"{normalized_left} {normalized_right}"


def _looks_like_terminal_final_caption(text: str) -> bool:
    normalized_text = text.strip()
    if not normalized_text:
        return False
    return bool(_FINAL_CAPTION_TERMINAL_PATTERN.search(normalized_text))


def _looks_like_continuation_final_caption(text: str) -> bool:
    normalized_text = text.strip()
    if not normalized_text:
        return False
    return bool(_FINAL_CAPTION_CONTINUATION_SUFFIX_PATTERN.search(normalized_text))
