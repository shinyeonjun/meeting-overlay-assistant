"""sherpa-onnx 실시간 벤치마크 래퍼 테스트."""

from __future__ import annotations

from pathlib import Path
from tests.fixtures.support.load_script import load_script_module


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "server" / "experiments" / "stt" / "benchmark_sherpa_streaming.py"
MODULE = load_script_module(SCRIPT_PATH)


class TestSherpaStreamingBenchmarkScript:
    def test_transducer_모델_아티팩트를_해결한다(self, tmp_path):
        (tmp_path / "tokens.txt").write_text("<blk> 0", encoding="utf-8")
        (tmp_path / "encoder-epoch-1.onnx").write_bytes(b"onnx")
        (tmp_path / "decoder-epoch-1.onnx").write_bytes(b"onnx")
        (tmp_path / "joiner-epoch-1.onnx").write_bytes(b"onnx")

        resolved = MODULE.resolve_transducer_artifacts(tmp_path)

        assert resolved["tokens"] == (tmp_path / "tokens.txt").resolve()
        assert resolved["encoder"] == (tmp_path / "encoder-epoch-1.onnx").resolve()
        assert resolved["decoder"] == (tmp_path / "decoder-epoch-1.onnx").resolve()
        assert resolved["joiner"] == (tmp_path / "joiner-epoch-1.onnx").resolve()

    def test_int8와_fp32가_같이_있으면_decoder만_fp32를_우선한다(self, tmp_path):
        (tmp_path / "tokens.txt").write_text("<blk> 0", encoding="utf-8")
        (tmp_path / "encoder-epoch-1.int8.onnx").write_bytes(b"onnx")
        (tmp_path / "encoder-epoch-1.onnx").write_bytes(b"onnx")
        (tmp_path / "decoder-epoch-1.int8.onnx").write_bytes(b"onnx")
        (tmp_path / "decoder-epoch-1.onnx").write_bytes(b"onnx")
        (tmp_path / "joiner-epoch-1.int8.onnx").write_bytes(b"onnx")
        (tmp_path / "joiner-epoch-1.onnx").write_bytes(b"onnx")

        resolved = MODULE.resolve_transducer_artifacts(tmp_path)

        assert resolved["encoder"] == (tmp_path / "encoder-epoch-1.int8.onnx").resolve()
        assert resolved["decoder"] == (tmp_path / "decoder-epoch-1.onnx").resolve()
        assert resolved["joiner"] == (tmp_path / "joiner-epoch-1.int8.onnx").resolve()

