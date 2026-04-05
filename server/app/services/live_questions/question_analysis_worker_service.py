"""실시간 질문 분석 워커 서비스."""

from __future__ import annotations

import logging

from server.app.services.live_questions.models import LiveQuestionResult


logger = logging.getLogger(__name__)


class LiveQuestionAnalysisWorkerService:
    """Redis 요청을 읽어 질문 분석 결과를 발행한다."""

    def __init__(
        self,
        *,
        queue,
        llm_client,
    ) -> None:
        self._queue = queue
        self._llm_client = llm_client

    def process_next_request(
        self,
        *,
        consumer_name: str,
        timeout_seconds: float,
    ) -> LiveQuestionResult | None:
        """대기 중인 질문 분석 요청 하나를 처리한다."""

        claimed = self._queue.claim_request(
            consumer_name=consumer_name,
            timeout_seconds=timeout_seconds,
        )
        if claimed is None:
            return None

        entry_id, request = claimed
        try:
            result = self._llm_client.analyze(request)
            self._queue.publish_result(result)
            return result
        except Exception:
            logger.exception(
                "실시간 질문 분석 실패: session_id=%s window_id=%s",
                request.session_id,
                request.window_id,
            )
            return None
        finally:
            self._queue.ack_request(entry_id)

    def warm_up(self) -> None:
        """worker 시작 시 질문 추출 모델을 미리 로드한다."""

        self._llm_client.warm_up()
