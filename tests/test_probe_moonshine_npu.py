"""Moonshine NPU probe 스크립트 보조 기능 테스트."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "backend" / "experiments" / "stt" / "probe_moonshine_npu.py"
SPEC = importlib.util.spec_from_file_location("probe_moonshine_npu", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class TestProbeMoonshineNpu:
    def test_input_shape_override를_파싱한다(self):
        overrides = MODULE.parse_input_shape_overrides(["input_features=1,80,3000"])

        assert overrides["input_features"] == (1, 80, 3000)

    def test_directory에서_onnx파일을_찾는다(self, tmp_path):
        model_dir = tmp_path / "onnx"
        model_dir.mkdir()
        model_path = model_dir / "encoder_model.onnx"
        model_path.write_bytes(b"onnx")

        resolved = MODULE.resolve_model_path(str(model_dir))

        assert resolved == model_path.resolve()

    def test_dummy_shape를_추론한다(self):
        shape = MODULE.infer_dummy_shape(["batch", "features", "frames"], "input_features")

        assert shape == (1, 80, 300)
