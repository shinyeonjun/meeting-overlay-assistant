"""엔트리포인트별 startup 계약 테스트"""

from fastapi.testclient import TestClient

from server.app.app_factory import create_app
from server.app.entrypoints.control_api import app as control_app
from server.app.entrypoints.live_api import app as live_app
from server.app.main import app as main_app


class TestEntrypoints:
    """엔트리포인트별 runtime/recovery 설정을 검증한다."""

    def test_control_api는_startup_recovery를_명시적으로_활성화한다(self):
        assert control_app.state.enable_live_runtime is False
        assert control_app.state.enable_startup_recovery is True

    def test_live_api는_live_runtime과_startup_recovery를_모두_활성화한다(self):
        assert live_app.state.enable_live_runtime is True
        assert live_app.state.enable_startup_recovery is True

    def test_main은_live_runtime과_startup_recovery를_모두_활성화한다(self):
        assert main_app.state.enable_live_runtime is True
        assert main_app.state.enable_startup_recovery is True

    def test_control_only_startup도_recovery_task를_실제로_실행한다(self, monkeypatch):
        calls: list[str] = []

        class FakeRecoveryService:
            async def recover_orphaned_running_sessions_async(self):
                calls.append("called")

        monkeypatch.setattr("server.app.app_factory.setup_logging", lambda *args, **kwargs: None)
        monkeypatch.setattr("server.app.app_factory.initialize_primary_persistence", lambda: None)
        monkeypatch.setattr(
            "server.app.app_factory.describe_primary_persistence_target",
            lambda: "test-target",
        )
        monkeypatch.setattr(
            "server.app.app_factory.get_session_recovery_service",
            lambda: FakeRecoveryService(),
        )

        app = create_app(
            include_control_routes=False,
            include_live_routes=False,
            enable_live_runtime=False,
            enable_startup_recovery=True,
        )

        with TestClient(app):
            pass

        assert calls == ["called"]

    def test_startup_recovery가_비활성화되면_recovery_task를_실행하지_않는다(self, monkeypatch):
        calls: list[str] = []

        class FakeRecoveryService:
            async def recover_orphaned_running_sessions_async(self):
                calls.append("called")

        monkeypatch.setattr("server.app.app_factory.setup_logging", lambda *args, **kwargs: None)
        monkeypatch.setattr("server.app.app_factory.initialize_primary_persistence", lambda: None)
        monkeypatch.setattr(
            "server.app.app_factory.describe_primary_persistence_target",
            lambda: "test-target",
        )
        monkeypatch.setattr(
            "server.app.app_factory.get_session_recovery_service",
            lambda: FakeRecoveryService(),
        )

        app = create_app(
            include_control_routes=False,
            include_live_routes=False,
            enable_live_runtime=False,
            enable_startup_recovery=False,
        )

        with TestClient(app):
            pass

        assert calls == []
