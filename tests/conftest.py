"""테스트 공통 fixture."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.api.http import dependencies as dependency_module
from backend.app.core.config import settings
from backend.app.infrastructure.persistence.sqlite.database import Database
import backend.app.main as main_module
from backend.app.main import app


@pytest.fixture
def temp_database_path(tmp_path: Path) -> Path:
    """테스트용 SQLite 경로를 준비한다."""
    return tmp_path / "test_meeting_overlay.db"


@pytest.fixture
def isolated_database(temp_database_path: Path):
    """테스트마다 독립된 SQLite 인스턴스를 제공한다."""
    test_database = Database(temp_database_path)
    test_database.initialize()

    original_main_database = main_module.database
    original_dependency_database = dependency_module.database
    original_topic_summarizer_backend = settings.topic_summarizer_backend
    original_analyzer_backend = settings.analyzer_backend
    original_stt_preload_on_startup = settings.stt_preload_on_startup
    main_module.database = test_database
    dependency_module.database = test_database
    object.__setattr__(settings, "topic_summarizer_backend", "noop")
    object.__setattr__(settings, "analyzer_backend", "rule_based")
    object.__setattr__(settings, "stt_preload_on_startup", False)
    dependency_module._get_shared_analyzer.cache_clear()
    dependency_module._get_shared_topic_summarizer.cache_clear()
    try:
        yield test_database
    finally:
        main_module.database = original_main_database
        dependency_module.database = original_dependency_database
        object.__setattr__(settings, "topic_summarizer_backend", original_topic_summarizer_backend)
        object.__setattr__(settings, "analyzer_backend", original_analyzer_backend)
        object.__setattr__(settings, "stt_preload_on_startup", original_stt_preload_on_startup)
        dependency_module._get_shared_analyzer.cache_clear()
        dependency_module._get_shared_topic_summarizer.cache_clear()


@pytest.fixture
def client(isolated_database):
    """FastAPI 테스트 클라이언트를 제공한다."""
    with TestClient(app) as test_client:
        yield test_client
