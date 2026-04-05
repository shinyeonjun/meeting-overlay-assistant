"""WAV fixture 하나로 세션 노트/리포트를 생성하는 개발용 스크립트."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.app.api.http.dependencies import initialize_primary_persistence
from server.app.api.http.dependency_providers.auth_context import get_session_service
from server.app.api.http.dependency_providers.reporting import (
    get_post_meeting_pipeline_service,
    get_report_generation_job_service,
    get_report_service,
    get_session_post_processing_job_service,
)
from server.app.api.http.wiring.persistence import get_event_repository, get_utterance_repository
from server.app.core.config import settings
from server.app.domain.shared.enums import AudioSource, SessionMode
from server.app.infrastructure.artifacts import LocalArtifactStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="fixture WAV 파일 하나로 세션 후처리와 리포트 생성을 실행합니다.",
    )
    parser.add_argument("--wav", required=True, help="원본 WAV 파일 경로")
    parser.add_argument(
        "--title",
        default="fixture 노트 생성 테스트",
        help="생성할 세션 제목",
    )
    parser.add_argument(
        "--workspace-id",
        default="workspace-default",
        help="세션을 저장할 workspace id",
    )
    parser.add_argument(
        "--skip-report",
        action="store_true",
        help="후처리까지만 실행하고 리포트 생성은 건너뜁니다.",
    )
    return parser


def convert_fixture_to_runtime_wav(*, source_path: Path, target_path: Path) -> None:
    """후처리 서비스가 기대하는 mono PCM WAV로 변환한다."""

    target_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source_path),
        "-ac",
        str(settings.stt_channels),
        "-ar",
        str(settings.stt_sample_rate_hz),
        "-sample_fmt",
        "s16",
        str(target_path),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "fixture WAV 변환에 실패했습니다. "
            f"stderr={completed.stderr.strip()}"
        )


def main() -> int:
    args = build_parser().parse_args()
    source_path = Path(args.wav).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"fixture WAV 파일을 찾을 수 없습니다: {source_path}")

    initialize_primary_persistence()

    session_service = get_session_service()
    post_meeting_pipeline_service = get_post_meeting_pipeline_service()
    session_post_processing_job_service = get_session_post_processing_job_service()
    report_generation_job_service = get_report_generation_job_service()
    report_service = get_report_service()
    utterance_repository = get_utterance_repository()
    event_repository = get_event_repository()
    artifact_store = LocalArtifactStore(settings.artifacts_root_path)

    session = session_service.create_session_draft(
        title=args.title,
        mode=SessionMode.MEETING,
        source=AudioSource.SYSTEM_AUDIO,
        workspace_id=args.workspace_id,
    )
    session = session_service.start_session(session.id)

    recording_artifact = artifact_store.build_recording_artifact(
        session_id=session.id,
        input_source=session.primary_input_source,
    )
    convert_fixture_to_runtime_wav(
        source_path=source_path,
        target_path=recording_artifact.file_path,
    )

    post_meeting_pipeline_service.finalize_session(
        session.id,
        workspace_id=args.workspace_id,
        resolved_by_user_id=None,
        dispatch_post_processing_job=False,
    )

    post_job = session_post_processing_job_service.process_latest_pending_for_session(
        session.id
    )
    latest_session = session_service.get_session(session.id)
    if latest_session is None:
        raise RuntimeError("세션 조회에 실패했습니다.")

    report_job = None
    if not args.skip_report and post_job is not None and post_job.status == "completed":
        report_job = report_generation_job_service.process_latest_pending_for_session(
            session.id
        )

    latest_session = session_service.get_session(session.id)
    final_status = report_generation_job_service.build_final_status(session=latest_session)
    latest_report = report_service.get_latest_report(session.id)
    latest_report_content = (
        report_service.read_report_content(latest_report)
        if latest_report is not None
        else None
    )
    transcript_items = utterance_repository.list_by_session(session.id)
    finalized_events = event_repository.list_by_session(session.id)

    print(
        json.dumps(
            {
                "session_id": session.id,
                "recording_artifact_id": recording_artifact.artifact_id,
                "recording_path": str(recording_artifact.file_path),
                "post_processing_status": latest_session.post_processing_status,
                "canonical_transcript_version": latest_session.canonical_transcript_version,
                "canonical_events_version": latest_session.canonical_events_version,
                "post_processing_job": (
                    {
                        "id": post_job.id,
                        "status": post_job.status,
                        "error_message": post_job.error_message,
                    }
                    if post_job is not None
                    else None
                ),
                "report_job": (
                    {
                        "id": report_job.id,
                        "status": report_job.status,
                        "error_message": report_job.error_message,
                    }
                    if report_job is not None
                    else None
                ),
                "final_report_status": {
                    "status": final_status.status,
                    "pipeline_stage": final_status.pipeline_stage,
                    "report_count": final_status.report_count,
                    "latest_report_id": final_status.latest_report_id,
                    "latest_file_path": final_status.latest_file_path,
                    "warning_reason": final_status.warning_reason,
                },
                "transcript_item_count": len(transcript_items),
                "event_count": len(finalized_events),
                "latest_report_preview": (
                    latest_report_content[:2000] if latest_report_content else None
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
