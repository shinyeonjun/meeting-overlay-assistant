"""세션 임시 녹음 파일 경로 유틸리티."""

from __future__ import annotations

from pathlib import Path

from server.app.core.config import ROOT_DIR


def get_session_recordings_dir(root_dir: Path | None = None) -> Path:
    """세션 임시 녹음 파일 저장 디렉터리를 반환한다."""

    base_dir = root_dir or ROOT_DIR
    return base_dir / "server" / "data" / "recordings"


def build_session_recording_path(
    session_id: str,
    input_source: str,
    *,
    root_dir: Path | None = None,
) -> Path:
    """세션과 입력 소스에 대응하는 임시 WAV 경로를 반환한다."""

    normalized_source = input_source.strip() or "unknown"
    safe_source = normalized_source.replace("\\", "-").replace("/", "-")
    return get_session_recordings_dir(root_dir) / f"{session_id}.{safe_source}.wav"


def find_session_recording_path(
    session_id: str,
    *,
    root_dir: Path | None = None,
) -> Path | None:
    """세션에 대응하는 임시 녹음 파일을 찾는다."""

    recordings_dir = get_session_recordings_dir(root_dir)
    if not recordings_dir.exists():
        return None

    candidates = sorted(
        recordings_dir.glob(f"{session_id}.*.wav"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None
