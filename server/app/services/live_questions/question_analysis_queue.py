"""공통 영역의 question analysis queue 서비스를 제공한다."""
from __future__ import annotations

from typing import Protocol

from server.app.services.live_questions.models import LiveQuestionRequest, LiveQuestionResult


class LiveQuestionAnalysisQueue(Protocol):
    """실시간 질문 요청/결과 큐 계약."""

    def publish_request(self, request: LiveQuestionRequest) -> bool:
        """질문 분석 요청을 큐에 적재한다."""

    def claim_request(
        self,
        *,
        consumer_name: str,
        timeout_seconds: float,
    ) -> tuple[str, LiveQuestionRequest] | None:
        """질문 분석 요청 하나를 소비자에게 할당한다."""

    def ack_request(self, entry_id: str) -> None:
        """처리된 질문 분석 요청을 확인 처리한다."""

    def publish_result(self, result: LiveQuestionResult) -> bool:
        """질문 분석 결과를 큐에 적재한다."""

    def claim_result(
        self,
        *,
        consumer_name: str,
        timeout_seconds: float,
    ) -> tuple[str, LiveQuestionResult] | None:
        """질문 분석 결과 하나를 소비자에게 할당한다."""

    def ack_result(self, entry_id: str) -> None:
        """처리된 질문 분석 결과를 확인 처리한다."""
