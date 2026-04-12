"""오디오 영역의 session recording 서비스를 제공한다."""
from __future__ import annotations

from pathlib import Path

from server.app.core.config import ROOT_DIR, settings
from server.app.infrastructure.artifacts import LocalArtifact, LocalArtifactStore


def get_session_recordings_dir(root_dir: Path | None = None) -> Path:
    """세션 녹음 artifact 디렉터리를 반환한다."""

    return _get_artifact_store(root_dir).get_recordings_dir()


def build_session_recording_artifact(
    session_id: str,
    input_source: str,
    *,
    root_dir: Path | None = None,
    artifact_store: LocalArtifactStore | None = None,
) -> LocalArtifact:
    """세션과 입력 소스 기준의 녹음 artifact를 만든다."""

    return _get_artifact_store(root_dir, artifact_store=artifact_store).build_recording_artifact(
        session_id=session_id,
        input_source=input_source,
    )


def build_session_recording_path(
    session_id: str,
    input_source: str,
    *,
    root_dir: Path | None = None,
) -> Path:
    """세션 녹음 artifact의 실제 파일 경로를 반환한다."""

    return build_session_recording_artifact(
        session_id,
        input_source,
        root_dir=root_dir,
    ).file_path


def find_session_recording_artifact(
    session_id: str,
    *,
    root_dir: Path | None = None,
    artifact_store: LocalArtifactStore | None = None,
) -> LocalArtifact | None:
    """세션의 최신 녹음 artifact를 찾는다."""

    resolved_store = _get_artifact_store(root_dir, artifact_store=artifact_store)
    artifact = resolved_store.find_latest_recording_artifact(session_id)
    if artifact is not None:
        return artifact

    legacy_path = _find_legacy_session_recording_path(session_id, root_dir=root_dir)
    if legacy_path is None:
        return None

    return LocalArtifact(
        artifact_id=None,
        file_path=legacy_path,
    )


def find_session_recording_path(
    session_id: str,
    *,
    root_dir: Path | None = None,
) -> Path | None:
    """세션의 최신 녹음 파일 경로를 찾는다."""

    artifact = find_session_recording_artifact(session_id, root_dir=root_dir)
    return artifact.file_path if artifact is not None else None


def resolve_recording_reference(
    *,
    artifact_id: str | None,
    fallback_path: str | Path | None = None,
    root_dir: Path | None = None,
    artifact_store: LocalArtifactStore | None = None,
) -> Path | None:
    """녹음 artifact id를 우선 해석하고, 없으면 fallback 경로를 사용한다."""

    return _get_artifact_store(root_dir, artifact_store=artifact_store).resolve_path_or_none(
        artifact_id,
        fallback_path=fallback_path,
    )


def _get_artifact_store(
    root_dir: Path | None,
    *,
    artifact_store: LocalArtifactStore | None = None,
) -> LocalArtifactStore:
    if artifact_store is not None:
        return artifact_store
    if root_dir is None:
        return LocalArtifactStore(settings.artifacts_root_path)
    return LocalArtifactStore(_resolve_project_root(root_dir) / "server" / "data" / "artifacts")


def _find_legacy_session_recording_path(
    session_id: str,
    *,
    root_dir: Path | None = None,
) -> Path | None:
    legacy_recordings_dir = _resolve_project_root(root_dir) / "server" / "data" / "recordings"
    if not legacy_recordings_dir.exists():
        return None

    candidates = sorted(
        legacy_recordings_dir.glob(f"{session_id}.*.wav"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _resolve_project_root(root_dir: Path | None) -> Path:
    return root_dir or ROOT_DIR
