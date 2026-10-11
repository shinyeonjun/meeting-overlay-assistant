"""벤치마크 스크립트 보조 기능 테스트."""

from __future__ import annotations

from pathlib import Path
from tests.fixtures.support.load_script import load_script_module


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "server" / "experiments" / "stt" / "benchmark_stt_backends.py"
MODULE = load_script_module(SCRIPT_PATH)


class TestBenchmarkScript:
    """벤치마크 스크립트의 인코딩 처리 동작을 검증한다."""

    def test_reference_file을_utf8로_읽는다(self, tmp_path):
        reference_path = tmp_path / "reference.txt"
        reference_path.write_text("안녕하세요 회의를 시작합니다.", encoding="utf-8")

        result = MODULE._read_text_file(reference_path)

        assert result == "안녕하세요 회의를 시작합니다."

    def test_resolve_reference_text가_상대경로를_해결한다(self, tmp_path):
        reference_path = tmp_path / "reference.txt"
        reference_path.write_text("정답 문장", encoding="utf-8")

        result = MODULE._resolve_reference_text(
            inline_text=None,
            reference_file="reference.txt",
            base_dir=tmp_path,
        )

        assert result == "정답 문장"

