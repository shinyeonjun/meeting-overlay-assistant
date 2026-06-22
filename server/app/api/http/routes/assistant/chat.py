"""assistant chat 라우트."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from server.app.api.http.dependencies import (
    get_assistant_chat_service,
    get_assistant_response_job_service,
)
from server.app.api.http.routes.retrieval.support import (
    resolve_workspace_id,
    to_search_item_response,
)
from server.app.api.http.schemas.assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantConversationListItemResponse,
    AssistantConversationListResponse,
    AssistantConversationMessageResponse,
    AssistantConversationResponse,
)
from server.app.api.http.security import require_authenticated_session
from server.app.domain.models.auth_session import AuthenticatedSession
from server.app.services.assistant.jobs import AssistantResponseJobStorageUnavailable

MAX_CHAT_LIMIT = 12

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=AssistantChatResponse)
def chat_with_assistant(
    request: AssistantChatRequest,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> AssistantChatResponse:
    """회의 자료 기반 읽기 전용 챗봇 답변을 생성한다."""

    normalized_query = request.query.strip()
    if not normalized_query:
        raise HTTPException(status_code=400, detail="질문을 입력해 주세요.")

    assistant_service = get_assistant_chat_service()
    if assistant_service is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "assistant 검색 서비스를 사용할 수 없습니다. "
                "RETRIEVAL_EMBEDDING_BACKEND=ollama 설정과 Ollama 임베딩 모델을 확인해 주세요."
            ),
        )

    workspace_id = resolve_workspace_id(auth_context)
    normalized_limit = max(1, min(request.limit, MAX_CHAT_LIMIT))
    assistant_response_job_service = get_assistant_response_job_service()
    if assistant_response_job_service is not None:
        try:
            submission = assistant_response_job_service.submit_question(
                workspace_id=workspace_id,
                query=normalized_query,
                source_types=tuple(request.source_types or ()),
                session_id=request.session_id,
                account_id=request.account_id,
                contact_id=request.contact_id,
                context_thread_id=request.context_thread_id,
                conversation_id=request.conversation_id,
                conversation_history=tuple(
                    {"role": item.role, "content": item.content}
                    for item in (request.history or [])
                ),
                user_id=auth_context.user.id if auth_context is not None else None,
                limit=normalized_limit,
                dispatch=True,
            )
            return AssistantChatResponse(
                query=normalized_query,
                conversation_id=submission.conversation.id,
                answer="",
                source_count=0,
                sources=[],
                status="pending",
                message_id=submission.assistant_message.id,
                job_id=submission.job.id,
            )
        except AssistantResponseJobStorageUnavailable:
            logger.warning(
                "assistant response job storage unavailable; falling back to inline answer",
                exc_info=True,
            )

    result = assistant_service.answer(
        workspace_id=workspace_id,
        query=normalized_query,
        source_types=tuple(request.source_types or ()),
        session_id=request.session_id,
        account_id=request.account_id,
        contact_id=request.contact_id,
        context_thread_id=request.context_thread_id,
        conversation_id=request.conversation_id,
        conversation_history=tuple(
            {"role": item.role, "content": item.content}
            for item in (request.history or [])
        ),
        user_id=auth_context.user.id if auth_context is not None else None,
        limit=normalized_limit,
    )
    return AssistantChatResponse(
        query=result.query,
        conversation_id=getattr(result, "conversation_id", None) or request.conversation_id,
        answer=result.answer,
        source_count=len(result.sources),
        sources=[to_search_item_response(item) for item in result.sources],
        status="completed",
    )


@router.get("/conversations", response_model=AssistantConversationListResponse)
def list_assistant_conversations(
    limit: int = Query(default=30, ge=1, le=100),
    account_id: str | None = None,
    contact_id: str | None = None,
    context_thread_id: str | None = None,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> AssistantConversationListResponse:
    """저장된 assistant 대화 목록을 최신순으로 조회한다."""

    assistant_service = get_assistant_chat_service()
    if assistant_service is None:
        raise HTTPException(status_code=503, detail="assistant 서비스를 사용할 수 없습니다.")

    workspace_id = resolve_workspace_id(auth_context)
    conversations = assistant_service.list_conversations(
        workspace_id=workspace_id,
        user_id=auth_context.user.id if auth_context is not None else None,
        account_id=account_id,
        contact_id=contact_id,
        context_thread_id=context_thread_id,
        limit=limit,
    )
    return AssistantConversationListResponse(
        conversations=[
            AssistantConversationListItemResponse(
                conversation_id=conversation.id,
                title=conversation.title,
                status=conversation.status,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
            )
            for conversation in conversations
        ],
    )


@router.get("/conversations/{conversation_id}", response_model=AssistantConversationResponse)
def get_assistant_conversation(
    conversation_id: str,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> AssistantConversationResponse:
    """저장된 assistant 대화 메시지를 조회한다."""

    assistant_service = get_assistant_chat_service()
    if assistant_service is None:
        raise HTTPException(status_code=503, detail="assistant 서비스를 사용할 수 없습니다.")

    workspace_id = resolve_workspace_id(auth_context)
    snapshot = assistant_service.get_conversation_messages(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
    )
    if snapshot is None:
        raise HTTPException(status_code=404, detail="저장된 assistant 대화를 찾을 수 없습니다.")

    conversation, messages = snapshot
    return AssistantConversationResponse(
        conversation_id=conversation.id,
        title=conversation.title,
        status=conversation.status,
        messages=[
            AssistantConversationMessageResponse(
                id=message.id,
                role=message.role,
                content=message.content,
                status=message.status,
                error_message=message.error_message,
                sources=message.sources_json or [],
                metadata=message.metadata_json or {},
                created_at=message.created_at,
                updated_at=message.updated_at,
            )
            for message in messages
        ],
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assistant_conversation(
    conversation_id: str,
    auth_context: AuthenticatedSession | None = Depends(require_authenticated_session),
) -> Response:
    """저장된 assistant 대화를 삭제한다."""

    assistant_service = get_assistant_chat_service()
    if assistant_service is None:
        raise HTTPException(status_code=503, detail="assistant 서비스를 사용할 수 없습니다.")

    workspace_id = resolve_workspace_id(auth_context)
    deleted = assistant_service.delete_conversation(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="assistant 대화를 찾을 수 없습니다.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
