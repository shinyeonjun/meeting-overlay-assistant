"""저장소의 독립 실행 스크립트를 테스트에서 모듈로 불러오는 helper."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_script_module(script_path: Path) -> ModuleType:
    """스크립트 파일을 파일 이름과 같은 모듈 이름으로 불러와 sys.modules에 등록한다."""

    spec = importlib.util.spec_from_file_location(script_path.stem, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
