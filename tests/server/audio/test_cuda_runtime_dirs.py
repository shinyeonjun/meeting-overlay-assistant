from __future__ import annotations

from server.app.contexts.live_capture.application.audio.stt.faster_whisper.model_runtime import (
    discover_cuda_bin_dirs,
)


def test_discover_cuda_bin_dirs_lists_only_existing_bin_folders(tmp_path) -> None:
    nvidia_root = tmp_path / "nvidia"
    (nvidia_root / "cublas" / "bin").mkdir(parents=True)
    (nvidia_root / "cudnn" / "bin").mkdir(parents=True)
    (nvidia_root / "cudnn" / "lib").mkdir(parents=True)  # bin이 없는 패키지는 무시한다.
    (nvidia_root / "stray.txt").write_text("", encoding="utf-8")

    bin_dirs = discover_cuda_bin_dirs([str(nvidia_root)])

    assert bin_dirs == [
        str(nvidia_root / "cublas" / "bin"),
        str(nvidia_root / "cudnn" / "bin"),
    ]


def test_discover_cuda_bin_dirs_returns_empty_when_nothing_installed(tmp_path) -> None:
    assert discover_cuda_bin_dirs([str(tmp_path / "missing")]) == []
