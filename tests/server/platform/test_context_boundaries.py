"""바운디드 컨텍스트 경계 검사: 컨텍스트 내부 모듈은 그 컨텍스트 밖에서 import하지 않는다."""

from __future__ import annotations

import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[3] / "server" / "app"
CONTEXTS_ROOT = APP_ROOT / "contexts"
INTERNAL_SUBPACKAGES = ("domain", "application")


def _context_names() -> list[str]:
    return sorted(
        path.name
        for path in CONTEXTS_ROOT.iterdir()
        if path.is_dir() and (path / "__init__.py").exists()
    )


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
        elif isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
    return modules


def test_컨텍스트의_내부_모듈은_그_컨텍스트_밖에서_import하지_않는다():
    contexts = _context_names()
    assert contexts, "컨텍스트 패키지를 찾지 못했습니다."

    violations: list[str] = []
    for path in APP_ROOT.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        inside_context = next(
            (name for name in contexts if (CONTEXTS_ROOT / name) in path.parents),
            None,
        )
        for module in _imported_modules(path):
            for name in contexts:
                if name == inside_context:
                    continue
                for sub in INTERNAL_SUBPACKAGES:
                    prefix = f"server.app.contexts.{name}.{sub}"
                    if module == prefix or module.startswith(prefix + "."):
                        violations.append(f"{path.relative_to(APP_ROOT.parent.parent)} -> {module}")

    assert violations == [], "컨텍스트 공개 API(server.app.contexts.<name>)만 import하세요:\n" + "\n".join(violations)
