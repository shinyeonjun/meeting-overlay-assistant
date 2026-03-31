"""Redis Streams 기반 실시간 질문 큐."""

from __future__ import annotations

import json
import logging
import math

from server.app.services.live_questions.models import LiveQuestionRequest, LiveQuestionResult

try:
    from redis import Redis
    from redis.exceptions import RedisError, ResponseError
except ImportError:  # pragma: no cover
    Redis = None

    class RedisError(Exception):
        """redis 패키지가 없을 때를 위한 대체 예외."""

    class ResponseError(RedisError):
        """응답 오류 대체 예외."""


logger = logging.getLogger(__name__)


class RedisLiveQuestionStreamQueue:
    """요청/결과를 Redis Streams로 전달한다."""

    def __init__(
        self,
        *,
        redis_client: Redis,
        request_stream_key: str,
        result_stream_key: str,
        request_group: str,
        result_group: str,
    ) -> None:
        self._redis_client = redis_client
        self._request_stream_key = request_stream_key
        self._result_stream_key = result_stream_key
        self._request_group = request_group
        self._result_group = result_group
        self._ensure_group(self._request_stream_key, self._request_group)
        self._ensure_group(self._result_stream_key, self._result_group)

    def publish_request(self, request: LiveQuestionRequest) -> bool:
        """질문 분석 요청을 발행한다."""

        return self._publish(self._request_stream_key, request.to_payload())

    def claim_request(
        self,
        *,
        consumer_name: str,
        timeout_seconds: float,
    ) -> tuple[str, LiveQuestionRequest] | None:
        """질문 분석 요청 하나를 소비자에게 할당한다."""

        claimed = self._claim(
            stream_key=self._request_stream_key,
            group_name=self._request_group,
            consumer_name=consumer_name,
            timeout_seconds=timeout_seconds,
        )
        if claimed is None:
            return None

        entry_id, payload = claimed
        return entry_id, LiveQuestionRequest.from_payload(payload)

    def ack_request(self, entry_id: str) -> None:
        """질문 분석 요청을 확인 처리한다."""

        self._ack(self._request_stream_key, self._request_group, entry_id)

    def publish_result(self, result: LiveQuestionResult) -> bool:
        """질문 분석 결과를 발행한다."""

        return self._publish(self._result_stream_key, result.to_payload())

    def claim_result(
        self,
        *,
        consumer_name: str,
        timeout_seconds: float,
    ) -> tuple[str, LiveQuestionResult] | None:
        """질문 분석 결과 하나를 소비자에게 할당한다."""

        claimed = self._claim(
            stream_key=self._result_stream_key,
            group_name=self._result_group,
            consumer_name=consumer_name,
            timeout_seconds=timeout_seconds,
        )
        if claimed is None:
            return None

        entry_id, payload = claimed
        return entry_id, LiveQuestionResult.from_payload(payload)

    def ack_result(self, entry_id: str) -> None:
        """질문 분석 결과를 확인 처리한다."""

        self._ack(self._result_stream_key, self._result_group, entry_id)

    def _publish(self, stream_key: str, payload: dict[str, object]) -> bool:
        try:
            self._redis_client.xadd(
                stream_key,
                {"payload": json.dumps(payload, ensure_ascii=False)},
            )
            return True
        except RedisError:
            logger.exception("실시간 질문 stream 발행 실패: stream=%s", stream_key)
            return False

    def _claim(
        self,
        *,
        stream_key: str,
        group_name: str,
        consumer_name: str,
        timeout_seconds: float,
    ) -> tuple[str, dict[str, object]] | None:
        timeout_ms = max(1000, math.ceil(timeout_seconds * 1000))
        try:
            response = self._redis_client.xreadgroup(
                groupname=group_name,
                consumername=consumer_name,
                streams={stream_key: ">"},
                count=1,
                block=timeout_ms,
            )
        except RedisError:
            logger.exception(
                "실시간 질문 stream 소비 실패: stream=%s group=%s",
                stream_key,
                group_name,
            )
            return None

        if not response:
            return None

        _, entries = response[0]
        if not entries:
            return None

        entry_id, fields = entries[0]
        raw_payload = fields.get(b"payload") or fields.get("payload")
        if isinstance(raw_payload, bytes):
            decoded = raw_payload.decode("utf-8", errors="ignore")
        else:
            decoded = str(raw_payload or "{}")
        return self._decode_entry_id(entry_id), json.loads(decoded)

    def _ack(self, stream_key: str, group_name: str, entry_id: str) -> None:
        try:
            self._redis_client.xack(stream_key, group_name, entry_id)
        except RedisError:
            logger.exception(
                "실시간 질문 stream ack 실패: stream=%s group=%s entry_id=%s",
                stream_key,
                group_name,
                entry_id,
            )

    def _ensure_group(self, stream_key: str, group_name: str) -> None:
        try:
            self._redis_client.xgroup_create(
                name=stream_key,
                groupname=group_name,
                id="0",
                mkstream=True,
            )
        except ResponseError as error:
            if "BUSYGROUP" not in str(error):
                raise

    @staticmethod
    def _decode_entry_id(entry_id: bytes | str) -> str:
        if isinstance(entry_id, bytes):
            return entry_id.decode("utf-8", errors="ignore")
        return str(entry_id)
