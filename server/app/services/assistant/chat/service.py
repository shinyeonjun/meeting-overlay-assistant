"""회의 자료 기반 RAG 챗봇 서비스."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from uuid import UUID

from server.app.domain.models.assistant_conversation import (
    AssistantConversation,
    AssistantMessage,
)
from server.app.repositories.contracts.assistant_conversation_repository import (
    AssistantConversationRepository,
)
from server.app.services.analysis.llm.contracts.llm_completion_client import (
    LLMCompletionClient,
)
from server.app.services.assistant.chat.history_context import (
    normalize_conversation_history,
)
from server.app.services.assistant.chat.models import (
    AssistantChatResult,
    AssistantTimeContext,
)
from server.app.services.assistant.chat.planning import (
    AssistantQueryPlanner,
    build_fast_query_plan,
    should_use_llm_planner,
)
from server.app.services.assistant.chat.retrieval import (
    DEFAULT_CONTEXT_LIMIT,
    DEFAULT_SEARCH_LIMIT,
    AssistantRagRetriever,
    AssistantSessionContextRetriever,
)
from server.app.services.assistant.chat.synthesis import AssistantAnswerSynthesizer
from server.app.services.retrieval import RetrievalQueryService


logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class _PersistedAssistantTurn:
    conversation_id: str
    conversation_history: tuple[dict[str, str], ...]
    assistant_message_id: str


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
        planner_fast_path_enabled: bool = False,
        assistant_conversation_repository: AssistantConversationRepository | None = None,
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
        self._planner_fast_path_enabled = planner_fast_path_enabled
        self._conversation_repository = assistant_conversation_repository

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
        conversation_id: str | None = None,
        conversation_history=(),
        user_id: str | None = None,
        limit: int | None = None,
    ) -> AssistantChatResult:
        """질문에 맞는 근거를 찾고, 근거 기반 답변을 반환한다."""

        normalized_query = query.strip()
        if not normalized_query:
            return AssistantChatResult(
                query=query,
                answer="",
                sources=[],
                conversation_id=conversation_id,
            )

        persisted_turn = self._begin_persisted_turn(
            workspace_id=workspace_id,
            query=normalized_query,
            conversation_id=conversation_id,
            conversation_history=conversation_history,
            user_id=user_id,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
        )
        if persisted_turn is not None:
            conversation_id = persisted_turn.conversation_id
            conversation_history = persisted_turn.conversation_history

        try:
            result = self._answer_from_rag(
                workspace_id=workspace_id,
                normalized_query=normalized_query,
                source_types=source_types,
                session_id=session_id,
                account_id=account_id,
                contact_id=contact_id,
                context_thread_id=context_thread_id,
                conversation_id=conversation_id,
                conversation_history=conversation_history,
                limit=limit,
            )
            self._complete_persisted_turn(persisted_turn, result)
            return result
        except Exception as exc:
            self._fail_persisted_turn(persisted_turn, exc)
            raise

    def get_conversation_messages(
        self,
        *,
        workspace_id: str,
        conversation_id: str,
        limit: int = 80,
    ):
        """저장된 대화와 메시지를 반환한다. 저장소가 없거나 미적용이면 None이다."""

        repository = self._conversation_repository
        normalized_conversation_id = _normalize_uuid_or_none(conversation_id)
        if repository is None or normalized_conversation_id is None:
            return None

        try:
            conversation = repository.get_conversation(
                conversation_id=normalized_conversation_id,
                workspace_id=workspace_id,
            )
            if conversation is None:
                return None
            messages = repository.list_messages(
                conversation_id=conversation.id,
                workspace_id=workspace_id,
                limit=limit,
            )
            return conversation, messages
        except Exception:
            logger.warning("assistant conversation storage is unavailable", exc_info=True)
            return None

    def generate_answer(
        self,
        *,
        workspace_id: str,
        query: str,
        source_types: tuple[str, ...] = (),
        session_id: str | None = None,
        account_id: str | None = None,
        contact_id: str | None = None,
        context_thread_id: str | None = None,
        conversation_id: str | None = None,
        conversation_history=(),
        limit: int | None = None,
    ) -> AssistantChatResult:
        """저장 부수효과 없이 RAG 답변만 생성한다."""

        return self._answer_from_rag(
            workspace_id=workspace_id,
            normalized_query=query.strip(),
            source_types=source_types,
            session_id=session_id,
            account_id=account_id,
            contact_id=contact_id,
            context_thread_id=context_thread_id,
            conversation_id=conversation_id,
            conversation_history=conversation_history,
            limit=limit,
        )

    def _answer_from_rag(
        self,
        *,
        workspace_id: str,
        normalized_query: str,
        source_types: tuple[str, ...],
        session_id: str | None,
        account_id: str | None,
        contact_id: str | None,
        context_thread_id: str | None,
        conversation_id: str | None,
        conversation_history,
        limit: int | None,
    ) -> AssistantChatResult:
        time_context = self._time_context_factory()
        normalized_history = normalize_conversation_history(conversation_history)
        if self._planner_fast_path_enabled and not should_use_llm_planner(normalized_query):
            plan = build_fast_query_plan(
                query=normalized_query,
                requested_source_types=source_types,
                conversation_history=normalized_history,
            )
        else:
            plan = self._planner.plan(
                query=normalized_query,
                time_context=time_context,
                requested_source_types=source_types,
                conversation_history=normalized_history,
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
                conversation_id=conversation_id,
            )

        answer = self._synthesizer.synthesize(
            plan=plan,
            sources=sources,
            time_context=time_context,
            conversation_history=normalized_history,
        )
        return AssistantChatResult(
            query=normalized_query,
            answer=answer,
            sources=sources,
            conversation_id=conversation_id,
        )

    def _begin_persisted_turn(
        self,
        *,
        workspace_id: str,
        query: str,
        conversation_id: str | None,
        conversation_history,
        user_id: str | None,
        account_id: str | None,
        contact_id: str | None,
        context_thread_id: str | None,
    ) -> _PersistedAssistantTurn | None:
        repository = self._conversation_repository
        if repository is None:
            return None

        try:
            conversation = AssistantConversation.create(
                conversation_id=_normalize_uuid_or_none(conversation_id),
                workspace_id=workspace_id,
                user_id=user_id,
                account_id=account_id,
                contact_id=contact_id,
                context_thread_id=context_thread_id,
                title=_build_conversation_title(query),
            )
            conversation = repository.upsert_conversation(conversation)
            stored_messages = repository.list_messages(
                conversation_id=conversation.id,
                workspace_id=workspace_id,
                limit=12,
                statuses=("completed",),
            )
            stored_history = tuple(
                {"role": message.role, "content": message.content}
                for message in stored_messages
                if message.role in {"user", "assistant"} and message.content
            )
            history = stored_history or normalize_conversation_history(conversation_history)

            repository.append_message(
                AssistantMessage.create(
                    conversation_id=conversation.id,
                    role="user",
                    content=query,
                )
            )
            assistant_message = repository.append_message(
                AssistantMessage.create(
                    conversation_id=conversation.id,
                    role="assistant",
                    content="",
                    status="pending",
                )
            )
            return _PersistedAssistantTurn(
                conversation_id=conversation.id,
                conversation_history=normalize_conversation_history(history),
                assistant_message_id=assistant_message.id,
            )
        except Exception:
            logger.warning("assistant conversation storage is unavailable", exc_info=True)
            return None

    def _complete_persisted_turn(
        self,
        persisted_turn: _PersistedAssistantTurn | None,
        result: AssistantChatResult,
    ) -> None:
        if persisted_turn is None or self._conversation_repository is None:
            return
        try:
            self._conversation_repository.update_message(
                message_id=persisted_turn.assistant_message_id,
                content=result.answer,
                status="completed",
                sources_json=_serialize_sources(result.sources),
                metadata_json={
                    "query": result.query,
                    "source_count": len(result.sources),
                },
            )
        except Exception:
            logger.warning("assistant message completion could not be persisted", exc_info=True)

    def _fail_persisted_turn(
        self,
        persisted_turn: _PersistedAssistantTurn | None,
        exc: Exception,
    ) -> None:
        if persisted_turn is None or self._conversation_repository is None:
            return
        try:
            self._conversation_repository.update_message(
                message_id=persisted_turn.assistant_message_id,
                content="",
                status="error",
                error_message=str(exc)[:1000],
                sources_json=[],
                metadata_json={},
            )
        except Exception:
            logger.warning("assistant message failure could not be persisted", exc_info=True)


def _normalize_uuid_or_none(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(UUID(str(value).strip()))
    except ValueError:
        return None


def _build_conversation_title(query: str) -> str:
    normalized = " ".join(query.split())
    if not normalized:
        return "Assistant conversation"
    if len(normalized) <= 80:
        return normalized
    return normalized[:79].rstrip() + "..."


def _serialize_sources(sources) -> list[dict]:
    return [asdict(source) for source in sources]
