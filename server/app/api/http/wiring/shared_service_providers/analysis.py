"""분석 계열 shared provider."""

from __future__ import annotations

from functools import lru_cache

from server.app.api.http.wiring import shared_factories
from server.app.api.http.wiring.persistence import get_event_repository, get_transaction_manager
from server.app.core.ai_service_profiles import (
    resolve_live_analyzer_service_profile,
    resolve_live_event_corrector_service_profile,
    resolve_post_processing_analyzer_service_profile,
    resolve_report_analyzer_service_profile,
)
from server.app.core.config import settings


@lru_cache(maxsize=1)
def get_shared_analyzer():
    """공용 analyzer singleton을 반환한다."""

    return get_shared_post_processing_analyzer()


@lru_cache(maxsize=1)
def get_shared_live_analyzer():
    """실시간 입력용 analyzer singleton을 반환한다."""

    return shared_factories.create_shared_analyzer(
        settings=settings,
        resolve_analyzer_service_profile=resolve_live_analyzer_service_profile,
    )


@lru_cache(maxsize=1)
def get_shared_post_processing_analyzer():
    """회의 후처리용 analyzer singleton을 반환한다."""

    return shared_factories.create_shared_analyzer(
        settings=settings,
        resolve_analyzer_service_profile=resolve_post_processing_analyzer_service_profile,
    )


@lru_cache(maxsize=1)
def get_shared_report_analyzer():
    """회의록 fallback용 analyzer singleton을 반환한다."""

    return shared_factories.create_shared_analyzer(
        settings=settings,
        resolve_analyzer_service_profile=resolve_report_analyzer_service_profile,
    )


@lru_cache(maxsize=1)
def get_shared_live_event_corrector():
    """공용 live event corrector singleton을 반환한다."""

    return shared_factories.create_shared_live_event_corrector(
        settings=settings,
        resolve_live_event_corrector_service_profile=resolve_live_event_corrector_service_profile,
        event_repository=get_event_repository(),
        transaction_manager=get_transaction_manager(),
    )
