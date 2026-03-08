"""Tauri 오버레이 구성 검증 테스트."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TAURI_CONFIG_PATH = PROJECT_ROOT / "frontend" / "src-tauri" / "tauri.conf.json"
OVERLAY_INDEX_PATH = PROJECT_ROOT / "frontend" / "overlay" / "index.html"


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

        assert config["build"]["devUrl"] == "http://127.0.0.1:1420"
        assert config["build"]["frontendDist"] == "../dist/overlay"
        assert '<script type="module" src="./src/main.js"></script>' in index_content
        assert "./src/main.js" in index_content
