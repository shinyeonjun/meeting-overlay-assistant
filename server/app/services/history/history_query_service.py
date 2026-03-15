"""history 조회 전용 서비스."""

from __future__ import annotations

from dataclasses import dataclass

from server.app.domain.retrieval import RetrievalSearchResult
from server.app.services.context.context_resolution_service import ContextResolutionService
from server.app.services.history.carry_over_service import CarryOverService, HistoryCarryOver
from server.app.services.reports.core.report_service import ReportService
from server.app.services.retrieval.query.retrieval_query_service import RetrievalQueryService
from server.app.services.sessions.session_service import SessionService


@dataclass(frozen=True)
class HistoryTimelineSnapshot:
    """history 타임라인 조회 결과."""

    account_id: str | None
    contact_id: str | None
    context_thread_id: str | None
    sessions: tuple[object, ...]
    reports: tuple[object, ...]
    carry_over: HistoryCarryOver
    retrieval_brief: "HistoryRetrievalBrief"


@dataclass(frozen=True)
class HistoryRetrievalBrief:
    """맥락 기반 retrieval 참고 문서 브리프."""

    query: str | None
    items: tuple[RetrievalSearchResult, ...]


class HistoryQueryService:
    """맥락 기준 history 타임라인을 조합한다."""

    def __init__(
        self,
        *,
        session_service: SessionService,
        report_service: ReportService,
        context_resolution_service: ContextResolutionService,
        carry_over_service: CarryOverService,
        retrieval_query_service: RetrievalQueryService | None = None,
        retrieval_limit: int = 4,
    ) -> None:
        self._session_service = session_service
        self._report_service = report_service
        self._context_resolution_service = context_resolution_service
        self._carry_over_service = carry_over_service
        self._retrieval_query_service = retrieval_query_service
        self._retrieval_limit = retrieval_limit

    def get_timeline(
        self,
        *,
        workspace_id: str,
        owner_filter: str | None,
        account_id: str | None,
        contact_id: str | None,
        context_thread_id: str | None,
        limit: int,
    ) -> HistoryTimelineSnapshot:
        """맥락 기준 타임라인과 carry-over를 계산한다."""

        self._context_resolution_service.resolve_session_context(
            workspace_id=workspace_id,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
        )
        sessions = tuple(
            self._session_service.list_sessions(
                created_by_user_id=owner_filter,
                account_id=account_id,
                contact_id=contact_id,
                context_thread_id=context_thread_id,
                limit=limit,
            )
        )
        reports = tuple(
            self._report_service.list_recent_reports(
                generated_by_user_id=owner_filter,
                account_id=account_id,
                contact_id=contact_id,
                context_thread_id=context_thread_id,
                limit=limit,
            )
        )

        carry_over = self._carry_over_service.build(sessions)
        retrieval_brief = self._build_retrieval_brief(
            workspace_id=workspace_id,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
            sessions=sessions,
            reports=reports,
            carry_over=carry_over,
        )

        return HistoryTimelineSnapshot(
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
            sessions=sessions,
            reports=reports,
            carry_over=carry_over,
            retrieval_brief=retrieval_brief,
        )

    def _build_retrieval_brief(
        self,
        *,
        workspace_id: str,
        account_id: str | None,
        contact_id: str | None,
        context_thread_id: str | None,
        sessions: tuple[object, ...],
        reports: tuple[object, ...],
        carry_over: HistoryCarryOver,
    ) -> HistoryRetrievalBrief:
        if self._retrieval_query_service is None:
            return HistoryRetrievalBrief(query=None, items=())

        if not any((account_id, contact_id, context_thread_id)):
            return HistoryRetrievalBrief(query=None, items=())

        query = self._build_brief_query(
            sessions=sessions,
            reports=reports,
            carry_over=carry_over,
        )
        if not query:
            return HistoryRetrievalBrief(query=None, items=())

        items = tuple(
            self._retrieval_query_service.search(
                workspace_id=workspace_id,
                query=query,
                account_id=account_id,
                contact_id=contact_id,
                context_thread_id=context_thread_id,
                limit=self._retrieval_limit,
            )
        )
        return HistoryRetrievalBrief(query=query, items=items)

    @staticmethod
    def _build_brief_query(
        *,
        sessions: tuple[object, ...],
        reports: tuple[object, ...],
        carry_over: HistoryCarryOver,
    ) -> str | None:
        phrases: list[str] = []
        seen: set[str] = set()

        def append_phrase(value: str | None) -> None:
            normalized = (value or "").strip()
            if not normalized or normalized in seen:
                return
            seen.add(normalized)
            phrases.append(normalized)

        for item in (
            *carry_over.decisions,
            *carry_over.action_items,
            *carry_over.risks,
            *carry_over.questions,
        ):
            append_phrase(item.title)
            if len(phrases) >= 6:
                break

        if not phrases:
            for session in sessions[:3]:
                append_phrase(getattr(session, "title", None))
            for report in reports[:2]:
                append_phrase(getattr(report, "report_type", None))

        if not phrases:
            return None
        return " ".join(phrases)
