"""리포트 산출물 경로와 artifact 파일 저장 helper."""

from __future__ import annotations

import json
from pathlib import Path

from server.app.infrastructure.artifacts import LocalArtifactStore
from server.app.services.reports.report_models import (
    PreparedReportContent,
    SavedReportArtifacts,
)


def build_output_destination(
    *,
    artifact_store: LocalArtifactStore | None,
    output_dir: Path,
    session_id: str,
    report_type: str,
    version: int,
) -> tuple[str | None, Path]:
    """리포트 출력 대상 경로와 artifact id를 계산한다."""

    if artifact_store is not None:
        artifact = artifact_store.build_report_artifact(
            session_id=session_id,
            report_type=report_type,
            version=version,
        )
        return artifact.artifact_id, artifact.file_path

    suffix = "md" if report_type == "markdown" else "pdf"
    session_dir = output_dir / session_id
    return None, session_dir / f"{report_type}.v{version}.{suffix}"


def write_pipeline_artifacts(
    *,
    output_path: Path,
    prepared: PreparedReportContent,
) -> SavedReportArtifacts:
    """전사/분석 산출물을 리포트 옆에 저장한다."""

    transcript_path: str | None = None
    analysis_path: str | None = None
    html_path: str | None = None
    artifacts_dir = output_path.parent / "artifacts"

    if prepared.html_content:
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        html_file_path = artifacts_dir / f"{output_path.stem}.html"
        html_file_path.write_text(prepared.html_content, encoding="utf-8")
        html_path = str(html_file_path)

    if prepared.transcript_markdown:
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        transcript_file_path = artifacts_dir / f"{output_path.stem}.transcript.md"
        transcript_file_path.write_text(prepared.transcript_markdown, encoding="utf-8")
        transcript_path = str(transcript_file_path)

    if prepared.analysis_snapshot is not None:
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        analysis_file_path = artifacts_dir / f"{output_path.stem}.analysis.json"
        analysis_file_path.write_text(
            json.dumps(prepared.analysis_snapshot, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        analysis_path = str(analysis_file_path)

    return SavedReportArtifacts(
        transcript_path=transcript_path,
        analysis_path=analysis_path,
        html_path=html_path,
    )

