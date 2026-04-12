"""오디오 영역의 test ryzenai runtime 동작을 검증한다."""
from pathlib import Path

from server.app.services.audio.stt import ryzenai_runtime
from server.app.services.audio.stt.ryzenai_runtime import (
    build_runtime_error_message,
    inspect_runtime,
)


class TestRyzenAIRuntime:
    """Ryzen AI 런타임 상태 점검 로직을 검증한다."""

    def test_설치_경로가_없으면_준비되지_않은_상태를_반환한다(self):
        status = inspect_runtime(r"D:\does-not-exist")

        assert status.installation_path is None
        assert status.is_ready is False

    def test_필수_파일이_있어도_모듈이_없으면_미준비_상태를_반환한다(
        self, tmp_path: Path, monkeypatch
    ):
        runtime_root = tmp_path / "RyzenAI" / "1.6.1"
        for relative_path in (
            Path("quicktest/quicktest.py"),
            Path("quicktest/test_model.onnx"),
            Path("voe-4.0-win_amd64/vaip_config.json"),
            Path("onnxruntime/bin/onnxruntime.dll"),
        ):
            file_path = runtime_root / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("stub", encoding="utf-8")

        monkeypatch.setattr(ryzenai_runtime, "_missing_modules", lambda: ("onnxruntime",))
        status = inspect_runtime(str(runtime_root))

        assert status.installation_path == runtime_root
        assert status.is_ready is False
        assert "onnxruntime" in status.missing_modules

    def test_오류_메시지에_설치_가이드가_포함된다(self, tmp_path: Path):
        runtime_root = tmp_path / "RyzenAI" / "1.6.1"
        runtime_root.mkdir(parents=True, exist_ok=True)

        status = inspect_runtime(str(runtime_root))
        message = build_runtime_error_message(status)

        assert str(runtime_root) in message
        assert "quicktest\\quicktest.py" in message

    def test_모듈이_없을_때는_설치_스크립트_가이드가_포함된다(self, tmp_path: Path, monkeypatch):
        runtime_root = tmp_path / "RyzenAI" / "1.6.1"
        for relative_path in (
            Path("quicktest/quicktest.py"),
            Path("quicktest/test_model.onnx"),
            Path("voe-4.0-win_amd64/vaip_config.json"),
            Path("onnxruntime/bin/onnxruntime.dll"),
        ):
            file_path = runtime_root / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("stub", encoding="utf-8")

        monkeypatch.setattr(
            ryzenai_runtime,
            "_missing_modules",
            lambda: ("onnxruntime", "ryzenai_dynamic_dispatch"),
        )
        status = inspect_runtime(str(runtime_root))
        message = build_runtime_error_message(status)

        assert "install_ryzenai_runtime.ps1" in message

