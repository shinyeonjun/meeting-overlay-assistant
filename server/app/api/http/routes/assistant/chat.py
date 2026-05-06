"""assistant chat 라우트."""

from fastapi import APIRouter, Depends, HTTPException

from server.app.api.http.dependencies import get_assistant_chat_service
from server.app.api.http.routes.retrieval.support import (
    resolve_workspace_id,
    to_search_item_response,
)
from server.app.api.http.schemas.assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
)
from server.app.api.http.security import require_authenticated_session
from server.app.domain.models.auth_session import AuthenticatedSession

MAX_CHAT_LIMIT = 12

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
    result = assistant_service.answer(
        workspace_id=workspace_id,
        query=normalized_query,
        source_types=tuple(request.source_types or ()),
        session_id=request.session_id,
        account_id=request.account_id,
        contact_id=request.contact_id,
        context_thread_id=request.context_thread_id,
        limit=normalized_limit,
    )
    return AssistantChatResponse(
        query=result.query,
        answer=result.answer,
        source_count=len(result.sources),
        sources=[to_search_item_response(item) for item in result.sources],
    )
