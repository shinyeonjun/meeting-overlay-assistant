"""벤치마크 영역의 test realtime benchmark script 동작을 검증한다."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "server" / "experiments" / "stt" / "benchmark_realtime_stt.py"
SPEC = importlib.util.spec_from_file_location("benchmark_realtime_stt", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class TestRealtimeBenchmarkScript:
    """RealtimeBenchmarkScript 동작을 검증한다."""
    def test_wrapper_profiles에_sherpa와_sensevoice가_포함된다(self):
        profiles = MODULE._load_realtime_wrapper_profiles()

        assert "sherpa_onnx_streaming" in profiles
        assert profiles["sherpa_onnx_streaming"].output_format == "simul_jsonl"
        assert "sensevoice_small_streaming" in profiles
        assert profiles["sensevoice_small_streaming"].output_format == "simul_jsonl"

    def test_backend_model_override를_파싱한다(self):
        overrides = MODULE._parse_backend_model_overrides(
            ["moonshine_streaming=moonshine/tiny-ko", "faster_whisper=model-x"]
        )

        assert overrides["moonshine_streaming"] == "moonshine/tiny-ko"
        assert overrides["faster_whisper"] == "model-x"

    def test_emit_interval_평균을_계산한다(self):
        average = MODULE._average_intervals([0.1, 0.5, 1.1])

        assert average == 0.5

    def test_wrapper_subprocess_env를_utf8로_고정한다(self):
        env = MODULE._build_wrapper_subprocess_env()

        assert env["PYTHONUTF8"] == "1"
        assert env["PYTHONIOENCODING"] == "utf-8"

    def test_reference_file을_읽는다(self, tmp_path):
        reference_path = tmp_path / "reference.txt"
        reference_path.write_text("안녕하세요", encoding="utf-8")

        value = MODULE._resolve_reference_text(None, str(reference_path))

        assert value == "안녕하세요"

    def test_whisper_out_txt_wrapper_output을_파싱한다(self):
        stdout_text = "\n".join(
            [
                "1200.5 0 800 안녕하세요",
                "2400.0 800 1600 반갑습니다",
            ]
        )

        parsed = MODULE._parse_whisper_out_txt(stdout_text)

        assert parsed["partial_count"] == 0
        assert parsed["final_count"] == 2
        assert parsed["first_final_latency_seconds"] == 1.2005
        assert parsed["final_transcript"] == "안녕하세요 반갑습니다"

    def test_simulstreaming_jsonl_wrapper_output을_파싱한다(self):
        stdout_text = "\n".join(
            [
                '{"text":"안녕","is_final":false,"emission_time":0.9}',
                '{"text":"안녕하세요","is_final":true,"emission_time":1.4}',
                '{"is_final":true,"emission_time":1.5}',
                '{"text":"반갑습니다","is_final":true,"emission_time":2.2}',
            ]
        )

        parsed = MODULE._parse_simulstreaming_jsonl(stdout_text)

        assert parsed["partial_count"] == 1
        assert parsed["final_count"] == 2
        assert parsed["first_partial_latency_seconds"] == 0.9
        assert parsed["first_final_latency_seconds"] == 1.4
        assert parsed["last_partial_transcript"] == "안녕"
        assert parsed["final_transcript"] == "안녕하세요 반갑습니다"

    def test_backend_instance_이름을_프로파일과_인스턴스로_분리한다(self):
        profile_name, instance_name = MODULE._split_backend_instance_name("sensevoice_small_streaming@cuda")

        assert profile_name == "sensevoice_small_streaming"
        assert instance_name == "cuda"

    def test_backend_arg_override를_리스트로_누적한다(self):
        overrides = MODULE._parse_repeated_override_map(
            [
                "sensevoice_small_streaming@cuda=--device",
                "sensevoice_small_streaming@cuda=cuda:0",
            ],
            "--backend-arg",
        )

        assert overrides["sensevoice_small_streaming@cuda"] == ["--device", "cuda:0"]

    def test_instance_override가_프로파일_override보다_우선한다(self):
        value = MODULE._resolve_override_value(
            "sensevoice_small_streaming@cuda",
            "sensevoice_small_streaming",
            {
                "sensevoice_small_streaming": "cpu",
                "sensevoice_small_streaming@cuda": "cuda:0",
            },
            "default",
        )

        assert value == "cuda:0"

    def test_backend_args는_프로파일과_인스턴스_값을_합친다(self):
        args = MODULE._resolve_backend_args(
            "sensevoice_small_streaming@cuda",
            "sensevoice_small_streaming",
            {
                "sensevoice_small_streaming": ["--chunk-ms", "120"],
                "sensevoice_small_streaming@cuda": ["--device", "cuda:0"],
            },
        )

        assert args == ["--chunk-ms", "120", "--device", "cuda:0"]

