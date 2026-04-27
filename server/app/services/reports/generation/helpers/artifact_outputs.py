"""회의록 산출물 경로와 artifact 파일 저장 helper."""

from __future__ import annotations

import json
from pathlib import Path

from server.app.infrastructure.artifacts import LocalArtifactStore
from server.app.services.reports.composition.report_document import (
    report_document_to_dict,
)
from server.app.services.reports.report_models import (
    PreparedReportContent,
    SavedReportArtifacts,
)

_ARTIFACTS_DIR_NAME = "artifacts"


def build_output_destination(
    *,
    artifact_store: LocalArtifactStore | None,
    output_dir: Path,
    session_id: str,
    report_type: str,
    version: int,
) -> tuple[str | None, Path]:
    """회의록 출력 대상 경로와 artifact id를 계산한다."""

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
    """전사/분석 산출물을 회의록 옆에 저장한다."""

    transcript_path: str | None = None
    analysis_path: str | None = None
    html_path: str | None = None
    document_path: str | None = None
    artifacts_dir = output_path.parent / _ARTIFACTS_DIR_NAME

    if prepared.report_document is not None:
        document_path = _write_json_artifact(
            artifacts_dir=artifacts_dir,
            file_name=f"{output_path.stem}.document.json",
            payload=report_document_to_dict(prepared.report_document),
        )

    if prepared.html_content:
        html_path = _write_text_artifact(
            artifacts_dir=artifacts_dir,
            file_name=f"{output_path.stem}.html",
            content=prepared.html_content,
        )

    if prepared.transcript_markdown:
        transcript_path = _write_text_artifact(
            artifacts_dir=artifacts_dir,
            file_name=f"{output_path.stem}.transcript.md",
            content=prepared.transcript_markdown,
        )

    if prepared.analysis_snapshot is not None:
        analysis_path = _write_json_artifact(
            artifacts_dir=artifacts_dir,
            file_name=f"{output_path.stem}.analysis.json",
            payload=prepared.analysis_snapshot,
        )

    return SavedReportArtifacts(
        transcript_path=transcript_path,
        analysis_path=analysis_path,
        html_path=html_path,
        document_path=document_path,
    )


def _write_text_artifact(
    *,
    artifacts_dir: Path,
    file_name: str,
    content: str,
) -> str:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifacts_dir / file_name
    artifact_path.write_text(content, encoding="utf-8")
    return str(artifact_path)


def _write_json_artifact(
    *,
    artifacts_dir: Path,
    file_name: str,
    payload: dict[str, object],
) -> str:
    return _write_text_artifact(
        artifacts_dir=artifacts_dir,
        file_name=file_name,
        content=json.dumps(payload, ensure_ascii=False, indent=2),
    )

