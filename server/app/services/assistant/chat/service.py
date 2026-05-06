"""읽기 전용 RAG 챗봇 서비스."""

from __future__ import annotations

from server.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)
from server.app.services.assistant.chat.models import (
    AssistantChatResult,
    AssistantTimeContext,
)
from server.app.services.assistant.chat.planning import AssistantQueryPlanner
from server.app.services.assistant.chat.retrieval import (
    DEFAULT_CONTEXT_LIMIT,
    DEFAULT_SEARCH_LIMIT,
    AssistantRagRetriever,
    AssistantSessionContextRetriever,
)
from server.app.services.assistant.chat.synthesis import AssistantAnswerSynthesizer
from server.app.services.retrieval import RetrievalQueryService


class AssistantChatService:
    """LLM planner -> hybrid RAG retrieval -> 답변 합성 순서로 답변한다."""

    def __init__(
        self,
        *,
        retrieval_query_service: RetrievalQueryService,
        completion_client: LLMCompletionClient,
        search_limit: int = DEFAULT_SEARCH_LIMIT,
        context_limit: int = DEFAULT_CONTEXT_LIMIT,
        planner: AssistantQueryPlanner | None = None,
        retriever: AssistantRagRetriever | None = None,
        session_context_retriever: AssistantSessionContextRetriever | None = None,
        synthesizer: AssistantAnswerSynthesizer | None = None,
        time_context_factory=AssistantTimeContext.now_kst,
        session_service=None,
    ) -> None:
        self._planner = planner or AssistantQueryPlanner(
            completion_client=completion_client,
        )
        self._retriever = retriever or AssistantRagRetriever(
            retrieval_query_service=retrieval_query_service,
            search_limit=search_limit,
            context_limit=context_limit,
        )
        self._session_context_retriever = (
            session_context_retriever
            if session_context_retriever is not None
            else (
                AssistantSessionContextRetriever(session_service=session_service)
                if session_service is not None
                else None
            )
        )
        self._synthesizer = synthesizer or AssistantAnswerSynthesizer(
            completion_client=completion_client,
        )
        self._time_context_factory = time_context_factory

    def answer(
        self,
        *,
        workspace_id: str,
        query: str,
        source_types: tuple[str, ...] = (),
        session_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
        limit: int | None = None,
    ) -> AssistantChatResult:
        """질문에 맞는 근거를 찾고, 근거 기반 답변을 반환한다."""

        normalized_query = query.strip()
        if not normalized_query:
            return AssistantChatResult(query=query, answer="", sources=[])

        time_context = self._time_context_factory()
        plan = self._planner.plan(
            query=normalized_query,
            time_context=time_context,
            requested_source_types=source_types,
        )
        sources = []
        if "sessions" in plan.retrieval_sources and self._session_context_retriever is not None:
            sources.extend(
                self._session_context_retriever.retrieve(
                    plan=plan,
                    time_context=time_context,
                    account_id=account_id,
                    contact_id=contact_id,
                    context_thread_id=context_thread_id,
                )
            )
        if "knowledge" in plan.retrieval_sources:
            sources.extend(
                self._retriever.retrieve(
                    workspace_id=workspace_id,
                    plan=plan,
                    requested_source_types=source_types,
                    session_id=session_id,
                    account_id=account_id,
                    contact_id=contact_id,
                    context_thread_id=context_thread_id,
                    limit=limit,
                )
            )
        if not sources:
            return AssistantChatResult(
                query=normalized_query,
                answer=(
                    "관련 회의 근거를 찾지 못했습니다. 회의 제목, 고객명, 날짜, 결정 사항 같은 "
                    "단서를 조금 더 구체적으로 넣어 다시 질문해 주세요."
                ),
                sources=[],
            )

        answer = self._synthesizer.synthesize(
            plan=plan,
            sources=sources,
            time_context=time_context,
        )
        return AssistantChatResult(
            query=normalized_query,
            answer=answer,
            sources=sources,
        )
