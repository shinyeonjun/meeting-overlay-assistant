"""Meeting event repository SQL helper."""

from __future__ import annotations

from server.app.domain.events import MeetingEvent
from server.app.domain.shared.enums import EventState, EventType


SELECT_COLUMNS = """
    SELECT
        id,
        session_id,
        source_utterance_id,
        event_type,
        title,
        normalized_title,
        body,
        evidence_text,
        speaker_label,
        state,
        input_source,
        insight_scope,
        CAST(EXTRACT(EPOCH FROM created_at) * 1000 AS BIGINT) AS created_at_ms,
        CAST(EXTRACT(EPOCH FROM updated_at) * 1000 AS BIGINT) AS updated_at_ms
    FROM overlay_events
"""


def build_list_by_session_query(
    session_id: str,
    *,
    insight_scope: str | None,
) -> tuple[str, tuple[object, ...]]:
    """세션 기준 이벤트 조회 쿼리를 만든다."""

    query = f"""
        {SELECT_COLUMNS}
        WHERE session_id = %s
    """
    params: list[object] = [session_id]
    if insight_scope is not None:
        query += " AND insight_scope = %s"
        params.append(insight_scope)
    query += " ORDER BY created_at ASC"
    return query, tuple(params)


def build_get_by_id_query(event_id: str) -> tuple[str, tuple[str]]:
    """단건 조회 쿼리를 만든다."""

    return (
        f"""
        {SELECT_COLUMNS}
        WHERE id = %s
        """,
        (event_id,),
    )


def build_list_by_source_utterance_query(
    session_id: str,
    source_utterance_id: str,
    *,
    insight_scope: str | None,
) -> tuple[str, tuple[object, ...]]:
    """source utterance 기준 이벤트 조회 쿼리를 만든다."""

    query = f"""
        {SELECT_COLUMNS}
        WHERE session_id = %s
          AND source_utterance_id = %s
    """
    params: list[object] = [session_id, source_utterance_id]
    if insight_scope is not None:
        query += " AND insight_scope = %s"
        params.append(insight_scope)
    query += " ORDER BY created_at ASC"
    return query, tuple(params)


def build_merge_lookup(candidate: MeetingEvent) -> tuple[str | None, tuple[object, ...]]:
    """중복 병합 대상 조회 쿼리를 만든다."""

    if candidate.event_type == EventType.TOPIC:
        return None, ()
    if candidate.event_type not in {
        EventType.QUESTION,
        EventType.DECISION,
        EventType.ACTION_ITEM,
        EventType.RISK,
    }:
        return None, ()
    return (
        f"""
        {SELECT_COLUMNS}
        WHERE session_id = %s
          AND event_type = %s
          AND normalized_title = %s
          AND insight_scope = %s
          AND state != %s
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (
            candidate.session_id,
            candidate.event_type.value,
            candidate.normalized_title,
            candidate.insight_scope,
            EventState.CLOSED.value,
        ),
    )
