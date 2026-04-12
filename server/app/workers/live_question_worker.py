"""실시간 질문 분석 워커."""

from __future__ import annotations

import argparse
import logging
import os
import socket

from server.app.api.http.wiring.live_question_queue import get_live_question_analysis_queue
from server.app.core.config import settings
from server.app.core.logging import setup_logging
from server.app.services.live_questions.question_analysis_worker_service import (
    LiveQuestionAnalysisWorkerService,
)
from server.app.services.live_questions.question_llm_client import LiveQuestionLLMClient


logger = logging.getLogger(__name__)


def build_default_worker_id() -> str:
    return f"{socket.gethostname()}-{os.getpid()}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CAPS live question worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="질문 분석 요청 하나만 처리한다.",
    )
    parser.add_argument(
        "--consumer-name",
        default=build_default_worker_id(),
        help="Redis consumer 이름",
    )
    parser.add_argument(
        "--block-seconds",
        type=float,
        default=max(settings.live_question_stream_block_seconds, 1),
        help="Redis stream에서 요청을 기다리는 최대 시간",
    )
    return parser


def build_worker_service() -> LiveQuestionAnalysisWorkerService:
    queue = get_live_question_analysis_queue()
    if queue is None:
        raise RuntimeError("실시간 질문 queue가 비활성화되어 있습니다.")

    llm_client = LiveQuestionLLMClient(
        backend_name=settings.live_question_llm_backend,
        model=settings.live_question_llm_model,
        base_url=settings.live_question_llm_base_url or "http://127.0.0.1:4000/v1",
        api_key=settings.live_question_llm_api_key,
        timeout_seconds=settings.live_question_llm_timeout_seconds,
    )
    return LiveQuestionAnalysisWorkerService(
        queue=queue,
        llm_client=llm_client,
    )


def main() -> int:
    args = build_parser().parse_args()
    setup_logging(
        level=settings.log_level,
        use_json=settings.log_json,
        log_file_path=settings.log_file_path,
    )
    worker = build_worker_service()

    if args.once:
        worker.process_next_request(
            consumer_name=args.consumer_name,
            timeout_seconds=args.block_seconds,
        )
        return 0

    logger.info(
        "실시간 질문 워커 시작: consumer=%s block_seconds=%s",
        args.consumer_name,
        args.block_seconds,
    )
    try:
        while True:
            worker.process_next_request(
                consumer_name=args.consumer_name,
                timeout_seconds=args.block_seconds,
            )
    except KeyboardInterrupt:
        logger.info("실시간 질문 워커 종료 요청을 받아 중단합니다.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
