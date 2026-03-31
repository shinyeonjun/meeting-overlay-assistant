"""리포트/요약 계열 shared provider."""

from __future__ import annotations

from functools import lru_cache

from server.app.api.http.wiring import shared_factories
from server.app.core.ai_service_profiles import (
    resolve_report_refiner_service_profile,
    resolve_topic_summarizer_service_profile,
)
from server.app.core.config import settings


@lru_cache(maxsize=1)
def get_shared_report_refiner():
    """공용 report refiner singleton을 반환한다."""

    return shared_factories.create_shared_report_refiner(
        settings=settings,
        resolve_report_refiner_service_profile=resolve_report_refiner_service_profile,
    )


@lru_cache(maxsize=1)
def get_shared_topic_summarizer():
    """공용 topic summarizer singleton을 반환한다."""

    return shared_factories.create_shared_topic_summarizer(
        settings=settings,
        resolve_topic_summarizer_service_profile=resolve_topic_summarizer_service_profile,
    )
