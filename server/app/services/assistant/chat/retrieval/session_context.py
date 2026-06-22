"""assistant 세션 메타데이터 context 검색."""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from server.app.domain.retrieval import RetrievalSearchResult
from server.app.services.assistant.chat.models import (
    AssistantQueryPlan,
    AssistantTimeContext,
)

MAX_SESSION_CONTEXT_ITEMS = 8


class AssistantSessionContextRetriever:
    """회의 목록/날짜 같은 구조화 세션 메타데이터를 RAG 근거로 만든다."""

    def __init__(
        self,
        *,
        session_service,
        recent_limit: int = 50,
        context_limit: int = MAX_SESSION_CONTEXT_ITEMS,
    ) -> None:
        self._session_service = session_service
        self._recent_limit = max(1, recent_limit)
        self._context_limit = max(1, context_limit)

    def retrieve(
        self,
        *,
        plan: AssistantQueryPlan,
        time_context: AssistantTimeContext,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
    ) -> list[RetrievalSearchResult]:
        """planner가 선택한 날짜/범위에 맞는 세션 목록을 synthetic source로 반환한다."""

        sessions = self._session_service.list_sessions(
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
            limit=self._recent_limit,
        )
        target_dates = set(plan.target_dates)
        target_months = _extract_target_months(plan.query, time_context)
        sorted_sessions = sorted(
            sessions,
            key=lambda session: _session_sort_key(session, time_context),
            reverse=True,
        )
        matched_sessions = [
            session
            for session in sorted_sessions
            if _matches_time_filters(
                session=session,
                time_context=time_context,
                target_dates=target_dates,
                target_months=target_months,
            )
        ][: self._context_limit]
        if not matched_sessions and not (target_dates or target_months):
            return []

        return [
            RetrievalSearchResult(
                chunk_id=_build_chunk_id(plan, target_months),
                document_id=_build_document_id(plan, target_months),
                source_type="session",
                source_id=_build_source_id(plan, target_months),
                document_title=_build_document_title(plan, target_months),
                chunk_text=_render_sessions(
                    sessions=matched_sessions,
                    target_dates=tuple(sorted(target_dates)),
                    target_months=tuple(sorted(target_months)),
                    time_context=time_context,
                ),
                chunk_heading="회의 목록",
                distance=0.0,
                metadata_json={
                    "kind": "session_lookup",
                    "target_dates": list(sorted(target_dates)),
                    "target_months": list(sorted(target_months)),
                    "session_ids": [str(session.id) for session in matched_sessions],
                    "knowledge_session_ids": _resolve_knowledge_session_ids(
                        plan=plan,
                        matched_sessions=matched_sessions,
                        target_dates=target_dates,
                        target_months=target_months,
                    ),
                    "session_scope": plan.session_scope,
                    "requires_knowledge": plan.requires_knowledge,
                },
            )
        ]


def _resolve_knowledge_session_ids(
    *,
    plan: AssistantQueryPlan,
    matched_sessions: list[object],
    target_dates: set[str],
    target_months: set[str],
) -> list[str]:
    if not matched_sessions or not plan.requires_knowledge:
        return []
    if target_dates or target_months:
        return [str(session.id) for session in matched_sessions]
    if plan.session_scope in {"latest", "previous"}:
        return [str(matched_sessions[0].id)]
    if plan.session_scope in {"recent_list", "date", "month", "title", "all"}:
        return [str(session.id) for session in matched_sessions]
    return []


def _render_sessions(
    *,
    sessions: list[object],
    target_dates: tuple[str, ...],
    target_months: tuple[str, ...],
    time_context: AssistantTimeContext,
) -> str:
    lines = ["# 회의 목록"]
    if target_dates:
        lines.append(f"- 조회 날짜(KST): {', '.join(target_dates)}")
    elif target_months:
        lines.append(f"- 조회 월(KST): {', '.join(target_months)}")
    else:
        lines.append("- 조회 범위: 최근 회의")
    lines.append(f"- 결과 수: {len(sessions)}")
    lines.append("")
    for index, session in enumerate(sessions, start=1):
        started_at = _format_session_time_kst(session, time_context)
        participants = ", ".join(getattr(session, "participants", ()) or ()) or "-"
        status = _enum_value(getattr(session, "status", None)) or "-"
        source = getattr(session, "primary_input_source", None) or "-"
        lines.extend(
            [
                f"## {index}. {getattr(session, 'title', '무제 회의')}",
                f"- 세션 ID: {getattr(session, 'id', '-')}",
                f"- 시작 시간(KST): {started_at}",
                f"- 상태: {status}",
                f"- 입력 소스: {source}",
                f"- 참여자: {participants}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def _session_date_kst(session: object, time_context: AssistantTimeContext) -> str | None:
    started_at = _parse_datetime(getattr(session, "started_at", ""))
    if started_at is None:
        return None
    return started_at.astimezone(time_context.now.tzinfo).date().isoformat()


def _session_month_kst(session: object, time_context: AssistantTimeContext) -> str | None:
    date_text = _session_date_kst(session, time_context)
    if not date_text:
        return None
    return date_text[:7]


def _session_sort_key(session: object, time_context: AssistantTimeContext) -> datetime:
    started_at = _parse_datetime(getattr(session, "started_at", ""))
    if started_at is None:
        return datetime.min.replace(tzinfo=time_context.now.tzinfo)
    return started_at.astimezone(time_context.now.tzinfo)


def _matches_time_filters(
    *,
    session: object,
    time_context: AssistantTimeContext,
    target_dates: set[str],
    target_months: set[str],
) -> bool:
    if target_dates:
        return _session_date_kst(session, time_context) in target_dates
    if target_months:
        return _session_month_kst(session, time_context) in target_months
    return True


def _extract_target_months(query: str, time_context: AssistantTimeContext) -> set[str]:
    months: set[str] = set()
    normalized = query.strip()
    for year, month in re.findall(r"(\d{4})\s*년?\s*(\d{1,2})\s*월", normalized):
        month_number = int(month)
        if 1 <= month_number <= 12:
            months.add(f"{int(year):04d}-{month_number:02d}")
    if months:
        return months

    for month in re.findall(r"(?<!\d)(\d{1,2})\s*월", normalized):
        month_number = int(month)
        if 1 <= month_number <= 12:
            months.add(f"{time_context.now.year:04d}-{month_number:02d}")
    return months


def _format_session_time_kst(session: object, time_context: AssistantTimeContext) -> str:
    started_at = _parse_datetime(getattr(session, "started_at", ""))
    if started_at is None:
        return "-"
    return started_at.astimezone(time_context.now.tzinfo).strftime("%Y-%m-%d %H:%M")


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _enum_value(value: object) -> str:
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    return str(value).strip() if value is not None else ""


def _build_chunk_id(plan: AssistantQueryPlan, target_months: set[str]) -> str:
    return f"session-lookup:{_build_lookup_scope(plan, target_months)}"


def _build_document_id(plan: AssistantQueryPlan, target_months: set[str]) -> str:
    return f"session-document:{_build_lookup_scope(plan, target_months)}"


def _build_source_id(plan: AssistantQueryPlan, target_months: set[str]) -> str:
    return f"sessions:{_build_lookup_scope(plan, target_months)}"


def _build_document_title(plan: AssistantQueryPlan, target_months: set[str]) -> str:
    if plan.target_dates:
        return f"{', '.join(plan.target_dates)} 회의 목록"
    if target_months:
        return f"{', '.join(sorted(target_months))} 회의 목록"
    return "최근 회의 목록"


def _build_lookup_scope(plan: AssistantQueryPlan, target_months: set[str]) -> str:
    if plan.target_dates:
        return ",".join(plan.target_dates)
    if target_months:
        return ",".join(sorted(target_months))
    return "recent"
