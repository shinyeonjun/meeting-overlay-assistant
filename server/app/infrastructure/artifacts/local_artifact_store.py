"""로컬 파일시스템 기반 artifact 저장소.

artifact id는 artifact 루트 기준의 POSIX 상대 경로다.
예: ``recordings/<session_id>/system_audio.wav``,
``reports/<session_id>/markdown/v1/report.md``.

DB에는 절대 경로 대신 artifact id를 저장하고, 실제 파일 경로는 이 저장소가
실행 환경의 루트 경로를 기준으로 해석한다. 저장소는 경로 계산만 담당하며,
디렉터리 생성과 파일 쓰기는 호출하는 쪽이 맡는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

RECORDINGS_DIR_NAME = "recordings"
REPORTS_DIR_NAME = "reports"
RECORDING_SUFFIX = ".wav"


@dataclass(frozen=True)
class LocalArtifact:
    """artifact id와 실제 파일 경로 묶음.

    ``artifact_id``가 ``None``이면 artifact 저장소 밖의 파일
    (예: 이전 버전 경로에서 찾은 녹음 파일)을 가리킨다.
    """

    artifact_id: str | None
    file_path: Path


class LocalArtifactStore:
    """artifact 루트 디렉터리 아래의 파일 경로 규칙을 관리한다."""

    def __init__(self, root_path: str | Path) -> None:
        self._root_path = Path(root_path)

    @property
    def root_path(self) -> Path:
        """artifact 루트 디렉터리를 반환한다."""

        return self._root_path

    # ------------------------------------------------------------------
    # 녹음 artifact
    # ------------------------------------------------------------------
    def get_recordings_dir(self) -> Path:
        """세션 녹음 artifact 디렉터리를 반환한다."""

        return self._root_path / RECORDINGS_DIR_NAME

    def build_recording_artifact(self, *, session_id: str, input_source: str) -> LocalArtifact:
        """세션과 입력 소스 기준의 녹음 artifact를 만든다."""

        artifact_id = _join_artifact_id(
            RECORDINGS_DIR_NAME,
            session_id,
            f"{input_source}{RECORDING_SUFFIX}",
        )
        return self._to_artifact(artifact_id)

    def find_latest_recording_artifact(self, session_id: str) -> LocalArtifact | None:
        """세션 녹음 디렉터리에서 가장 최근에 수정된 wav 파일을 찾는다."""

        _validate_segment(session_id)
        session_dir = self.get_recordings_dir() / session_id
        if not session_dir.is_dir():
            return None

        candidates = [path for path in session_dir.glob(f"*{RECORDING_SUFFIX}") if path.is_file()]
        if not candidates:
            return None

        latest = max(candidates, key=lambda path: (path.stat().st_mtime_ns, path.name))
        artifact_id = _join_artifact_id(RECORDINGS_DIR_NAME, session_id, latest.name)
        return LocalArtifact(artifact_id=artifact_id, file_path=latest)

    # ------------------------------------------------------------------
    # 리포트 artifact
    # ------------------------------------------------------------------
    def build_report_artifact(
        self,
        *,
        session_id: str,
        report_type: str,
        version: int,
    ) -> LocalArtifact:
        """세션/리포트 종류/버전 기준의 리포트 artifact를 만든다."""

        if version < 1:
            raise ValueError(f"리포트 버전은 1 이상이어야 합니다: {version}")
        suffix = "md" if report_type == "markdown" else "pdf"
        artifact_id = _join_artifact_id(
            REPORTS_DIR_NAME,
            session_id,
            report_type,
            f"v{version}",
            f"report.{suffix}",
        )
        return self._to_artifact(artifact_id)

    # ------------------------------------------------------------------
    # 경로 해석
    # ------------------------------------------------------------------
    def resolve_path(self, artifact_id: str) -> Path:
        """artifact id를 루트 기준 실제 경로로 바꾼다.

        루트 밖을 가리키는 id(절대 경로, ``..`` 포함)는 거부한다.
        """

        if not artifact_id or not artifact_id.strip():
            raise ValueError("artifact id가 비어 있습니다.")

        normalized = artifact_id.replace("\\", "/")
        if PurePosixPath(normalized).is_absolute() or ":" in normalized.split("/", 1)[0]:
            raise ValueError(f"artifact id는 상대 경로여야 합니다: {artifact_id}")
        parts = normalized.split("/")
        if any(part in ("", ".", "..") for part in parts):
            raise ValueError(f"허용되지 않는 artifact id입니다: {artifact_id}")

        resolved = self._root_path.joinpath(*parts)
        root = self._root_path.resolve()
        if not resolved.resolve().is_relative_to(root):
            raise ValueError(f"artifact 루트 밖을 가리키는 id입니다: {artifact_id}")
        return resolved

    def resolve_path_or_none(
        self,
        artifact_id: str | None,
        *,
        fallback_path: str | Path | None = None,
    ) -> Path | None:
        """artifact id를 우선 해석하고, 없으면 fallback 경로를 반환한다."""

        if artifact_id:
            return self.resolve_path(artifact_id)
        if fallback_path:
            return Path(fallback_path)
        return None

    def _to_artifact(self, artifact_id: str) -> LocalArtifact:
        return LocalArtifact(artifact_id=artifact_id, file_path=self.resolve_path(artifact_id))


def _join_artifact_id(*segments: str) -> str:
    for segment in segments:
        _validate_segment(segment)
    return "/".join(segments)


def _validate_segment(segment: str) -> None:
    if not segment or segment in (".", "..") or "/" in segment or "\\" in segment:
        raise ValueError(f"artifact 경로 구성 요소가 올바르지 않습니다: {segment!r}")
