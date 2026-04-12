"""벤치마크 영역의 test sensevoice benchmark script 동작을 검증한다."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "server" / "experiments" / "stt" / "benchmark_sensevoice_small.py"
SPEC = importlib.util.spec_from_file_location("benchmark_sensevoice_small", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class TestSenseVoiceBenchmarkScript:
    """SenseVoiceBenchmarkScript 동작을 검증한다."""
    def test_normalize_text가_공백을_정리한다(self):
        assert MODULE.normalize_text("  안녕   하세요  ") == "안녕 하세요"

