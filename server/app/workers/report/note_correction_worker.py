"""노트 보정 job을 별도 프로세스에서 처리하는 워커."""

from __future__ import annotations

import argparse
import logging
import os
import socket
import time

from server.app.api.http.dependencies import (
    get_note_correction_job_service,
    initialize_primary_persistence,
)
from server.app.core.config import settings
from server.app.core.logging import setup_logging
from server.app.workers.job_lease_heartbeat import JobLeaseHeartbeat


logger = logging.getLogger(__name__)


def build_default_worker_id() -> str:
    return f"{socket.gethostname()}-{os.getpid()}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CAPS note correction worker")
    parser.add_argument("--once", action="store_true", help="claim 가능한 job만 한 번 조회해서 처리합니다.")
    parser.add_argument("--batch-size", type=int, default=1, help="한 번에 claim할 job 개수입니다.")
    parser.add_argument("--lease-seconds", type=int, default=120, help="worker가 claim한 job lease 유지 시간입니다.")
    parser.add_argument(
        "--queue-block-seconds",
        type=float,
        default=max(settings.note_correction_job_queue_block_seconds, 1),
        help="Redis 큐에서 job 신호를 기다리는 최대 시간입니다.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=max(settings.note_correction_job_fallback_poll_seconds, 1),
        help="Redis 신호가 없어도 DB sweep으로 복구 확인하는 간격입니다.",
    )
    parser.add_argument(
        "--worker-id",
        default=build_default_worker_id(),
        help="분산 처리에서 claim 주체를 식별하는 worker id입니다.",
    )
    return parser


def _resolve_heartbeat_interval_seconds(lease_seconds: int) -> float:
    return max(
        1.0,
        min(
            float(settings.pipeline_job_heartbeat_interval_seconds),
            max(lease_seconds / 2.0, 1.0),
        ),
    )


def run_once(
    *,
    worker_id: str,
    batch_size: int,
    lease_seconds: int,
    idle_log_level: int = logging.DEBUG,
) -> int:
    service = get_note_correction_job_service()
    claimed_jobs = service.claim_available_jobs(
        worker_id=worker_id,
        lease_duration_seconds=lease_seconds,
        limit=batch_size,
    )
    if not claimed_jobs:
        logger.log(
            idle_log_level,
            "claim 가능한 note correction job이 없습니다: worker_id=%s",
            worker_id,
        )
        return 0

    heartbeat_interval_seconds = _resolve_heartbeat_interval_seconds(lease_seconds)
    processed_jobs = []
    for claimed_job in claimed_jobs:
        heartbeat = JobLeaseHeartbeat(
            interval_seconds=heartbeat_interval_seconds,
            renew_lease=lambda job_id=claimed_job.id: service.renew_job_lease(
                job_id=job_id,
                worker_id=worker_id,
                lease_duration_seconds=lease_seconds,
            ),
            logger=logger,
            worker_name="note correction worker",
            job_id=claimed_job.id,
        )
        with heartbeat.running():
            processed_jobs.append(
                service.process_job(claimed_job.id, expected_worker_id=worker_id)
            )

    for job in processed_jobs:
        logger.info(
            "note correction job 처리 완료: worker_id=%s job_id=%s session_id=%s status=%s attempts=%s",
            worker_id,
            job.id,
            job.session_id,
            job.status,
            job.attempt_count,
        )
    return len(processed_jobs)


def main() -> int:
    args = build_parser().parse_args()
    setup_logging(
        level=settings.log_level,
        use_json=settings.log_json,
        log_file_path=settings.log_file_path,
    )
    initialize_primary_persistence()

    batch_size = max(args.batch_size, 1)
    lease_seconds = max(args.lease_seconds, 5)
    queue_block_seconds = max(args.queue_block_seconds, 1.0)
    poll_interval_seconds = max(args.poll_interval_seconds, 0.5)
    worker_id = str(args.worker_id).strip() or build_default_worker_id()
    service = get_note_correction_job_service()
    queue_enabled = service.has_queue

    if args.once:
        run_once(
            worker_id=worker_id,
            batch_size=batch_size,
            lease_seconds=lease_seconds,
            idle_log_level=logging.INFO,
        )
        return 0

    logger.info(
        "note correction worker 시작: worker_id=%s batch_size=%s lease_seconds=%s queue_block_seconds=%s fallback_poll_seconds=%s queue_enabled=%s",
        worker_id,
        batch_size,
        lease_seconds,
        queue_block_seconds,
        poll_interval_seconds,
        queue_enabled,
    )

    try:
        last_sweep_at = 0.0
        while True:
            dispatched_job_id = service.wait_for_dispatched_job(queue_block_seconds)
            should_sweep = False

            if dispatched_job_id is not None:
                logger.info(
                    "note correction job 신호 수신: worker_id=%s job_id=%s",
                    worker_id,
                    dispatched_job_id,
                )
                should_sweep = True
            elif (not queue_enabled) or (time.monotonic() - last_sweep_at >= poll_interval_seconds):
                should_sweep = True

            if not should_sweep:
                continue

            processed_count = run_once(
                worker_id=worker_id,
                batch_size=batch_size,
                lease_seconds=lease_seconds,
                idle_log_level=logging.DEBUG,
            )
            last_sweep_at = time.monotonic()

            if processed_count == 0 and not queue_enabled:
                time.sleep(poll_interval_seconds)
    except KeyboardInterrupt:
        logger.info("note correction worker 종료 요청을 받아 중단합니다.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
