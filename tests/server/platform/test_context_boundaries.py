"""바운디드 컨텍스트 경계 검사: 컨텍스트 내부 모듈은 그 컨텍스트 밖에서 import하지 않는다."""

from __future__ import annotations

import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[3] / "server" / "app"
CONTEXT_ROOT = APP_ROOT / "contexts" / "context"
INTERNAL_PREFIXES = ("server.app.contexts.context.domain", "server.app.contexts.context.application")


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
        elif isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
    return modules


def test_맥락_컨텍스트의_내부_모듈은_밖에서_import하지_않는다():
    violations: list[str] = []
    for path in APP_ROOT.rglob("*.py"):
        if "__pycache__" in path.parts or CONTEXT_ROOT in path.parents:
            continue
        for module in _imported_modules(path):
            if module.startswith(INTERNAL_PREFIXES):
                violations.append(f"{path.relative_to(APP_ROOT.parent.parent)} -> {module}")

    assert violations == [], "컨텍스트 공개 API(server.app.contexts.context)만 import하세요:\n" + "\n".join(violations)
