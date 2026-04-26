"""Tauri 오버레이 구성 검증 테스트."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TAURI_CONFIG_PATH = PROJECT_ROOT / "client" / "overlay" / "src-tauri" / "tauri.conf.json"
OVERLAY_INDEX_PATH = PROJECT_ROOT / "client" / "overlay" / "index.html"
CLIENT_PACKAGE_PATH = PROJECT_ROOT / "client" / "overlay" / "package.json"


class TestOverlayUi:
    """정적 서빙 제거와 Tauri 구성을 검증한다."""

    def test_backend가_overlay_route를_더이상_서빙하지_않는다(self, client):
        response = client.get("/overlay/")

        assert response.status_code == 404

    def test_tauri_dev_origin_cors_preflight를_허용한다(self, client):
        response = client.options(
            "/api/v1/sessions",
            headers={
                "Origin": "http://127.0.0.1:1420",
                "Access-Control-Request-Method": "POST",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:1420"

    def test_tauri_dev_url과_overlay_index가_정상이다(self):
        config = json.loads(TAURI_CONFIG_PATH.read_text(encoding="utf-8"))
        index_content = OVERLAY_INDEX_PATH.read_text(encoding="utf-8")
        package_data = json.loads(CLIENT_PACKAGE_PATH.read_text(encoding="utf-8"))

        assert config["build"]["devUrl"] == "http://127.0.0.1:1420"
        assert config["build"]["frontendDist"] == "../dist/overlay"
        assert package_data["name"] == "caps-overlay-client"
        assert '<script type="module" src="./src/main.js"></script>' in index_content
        assert 'id="auth-gate"' in index_content
        assert 'id="server-url-input"' in index_content
        assert 'id="auth-login-form"' in index_content
        assert 'id="auth-remember-login"' in index_content
        assert 'id="logout-btn"' in index_content
        assert 'id="session-status"' in index_content
        assert 'id="session-participants"' in index_content
        assert 'id="session-account"' in index_content
        assert 'id="session-contact"' in index_content
        assert 'id="session-thread"' in index_content
        assert 'id="session-context-refresh-btn"' in index_content
        assert 'id="session-context-status"' in index_content
        assert 'id="create-session-btn"' in index_content
        assert 'id="start-session-btn"' in index_content
        assert 'id="end-session-btn"' in index_content
        assert 'id="session-participants-summary"' in index_content
        assert 'id="session-participant-candidates-panel"' in index_content
        assert 'id="session-participant-candidates-status"' in index_content
        assert 'id="session-participant-candidates-list"' in index_content
        assert 'id="session-participant-followups-panel"' in index_content
        assert 'id="session-participant-followups-status"' in index_content
        assert 'id="session-participant-followups-list"' in index_content
        assert 'id="open-web-workspace-btn"' in index_content
        assert 'id="workflow-summary-panel"' in index_content
        assert 'id="tab-session"' in index_content
        assert 'id="tab-events"' in index_content
        assert 'id="report-status"' in index_content
        assert 'id="report-file-path"' in index_content
