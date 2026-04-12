"""실시간 질문 shared provider."""

from __future__ import annotations

from functools import lru_cache

from server.app.api.http.wiring.live_question_queue import get_live_question_analysis_queue
from server.app.core.config import settings
from server.app.services.live_questions import (
    LiveQuestionDispatchService,
    LiveQuestionStateStore,
    NoOpLiveQuestionDispatchService,
)


@lru_cache(maxsize=1)
def get_shared_live_question_state_store():
    """실시간 질문 상태 저장소 singleton을 반환한다."""

    return LiveQuestionStateStore()


@lru_cache(maxsize=1)
def get_shared_live_question_dispatcher():
    """실시간 질문 디스패처 singleton을 반환한다."""

    queue = get_live_question_analysis_queue()
    if not settings.live_question_analysis_enabled or queue is None:
        return NoOpLiveQuestionDispatchService()

    return LiveQuestionDispatchService(
        queue=queue,
        state_store=get_shared_live_question_state_store(),
        debounce_ms=settings.live_question_debounce_ms,
        window_size=settings.live_question_window_size,
    )
