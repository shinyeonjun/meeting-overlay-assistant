"""맥락(Context) 바운디드 컨텍스트의 공개 API.

회사(계정), 상대방(연락처), 스레드와 그 유스케이스를 제공한다.
다른 컨텍스트와 바깥 계층은 이 패키지만 import한다. domain/application 내부 모듈을 직접 import하지 않는다.
"""

from server.app.contexts.context.application import (
    ContextCatalogService,
    ContextResolutionService,
    MeetingContextService,
)
from server.app.contexts.context.domain import (
    AccountContext,
    ContactContext,
    ContextThread,
    DuplicateAccountNameError,
    ResolvedMeetingContext,
)

__all__ = [
    "AccountContext",
    "ContactContext",
    "ContextCatalogService",
    "ContextResolutionService",
    "ContextThread",
    "DuplicateAccountNameError",
    "MeetingContextService",
    "ResolvedMeetingContext",
]
