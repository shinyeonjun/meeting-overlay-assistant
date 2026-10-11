"""SenseVoice-Small 벤치마크 래퍼 테스트."""

from __future__ import annotations

from pathlib import Path
from tests.fixtures.support.load_script import load_script_module


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "server" / "experiments" / "stt" / "benchmark_sensevoice_small.py"
MODULE = load_script_module(SCRIPT_PATH)


class TestSenseVoiceBenchmarkScript:
    def test_normalize_text가_공백을_정리한다(self):
        assert MODULE.normalize_text("  안녕   하세요  ") == "안녕 하세요"

