"""HTTP 계층에서 공통 관련 artifact storage 구성을 담당한다."""
from __future__ import annotations

from functools import lru_cache

from server.app.core.config import settings
from server.app.infrastructure.artifacts import LocalArtifactStore


@lru_cache(maxsize=1)
def get_local_artifact_store() -> LocalArtifactStore:
    """로컬 artifact storage를 캐시해서 반환한다."""

    return LocalArtifactStore(settings.artifacts_root_path)
