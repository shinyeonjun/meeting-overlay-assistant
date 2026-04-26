"""실시간 질문 감지 요청 dispatcher."""

from __future__ import annotations

import logging
import threading

from server.app.services.live_questions.models import LiveQuestionRequest, LiveQuestionUtterance
from server.app.services.live_questions.question_lane_filter import (
    QuestionLaneFilter,
    build_window_signature,
)

logger = logging.getLogger(__name__)


class NoOpLiveQuestionDispatchService:
    """질문 감지가 비활성화된 경우 사용하는 no-op dispatcher."""

    def submit(self, utterance) -> None:
        return None

    def shutdown(self) -> None:
        return None


class LiveQuestionDispatchService:
    """세션별 안정화 발화 window를 질문 감지 요청으로 보낸다."""

    def __init__(
        self,
        *,
        queue,
        state_store,
        debounce_ms: int,
        window_size: int,
        text_normalizer=None,
        lane_filter: QuestionLaneFilter | None = None,
    ) -> None:
        self._queue = queue
        self._state_store = state_store
        self._debounce_seconds = max(debounce_ms, 0) / 1000
        self._window_size = max(window_size, 1)
        self._text_normalizer = text_normalizer
        self._lane_filter = lane_filter or QuestionLaneFilter()
        self._lock = threading.Lock()
        self._buffers: dict[str, list[LiveQuestionUtterance]] = {}
        self._timers: dict[str, threading.Timer] = {}
        self._last_request_signatures: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {}

    def submit(self, utterance) -> None:
        """실시간 발화를 세션 buffer에 넣고 debounce 후 질문 감지 요청을 만든다."""

        snapshot = LiveQuestionUtterance.from_utterance(utterance)
        if self._text_normalizer is not None:
            snapshot = self._text_normalizer.normalize_utterance(snapshot)

        decision = self._lane_filter.decide(snapshot)
        if not decision.keep:
            logger.debug(
                "실시간 질문 lane 입력 제외: session_id=%s utterance_id=%s reason=%s",
                utterance.session_id,
                utterance.id,
                decision.reason,
            )
            return

        session_id = utterance.session_id
        with self._lock:
            buffer = self._buffers.setdefault(session_id, [])
            buffer.append(snapshot)
            if len(buffer) > self._window_size:
                del buffer[:-self._window_size]

            timer = self._timers.get(session_id)
            if timer is not None:
                timer.cancel()

            timer = threading.Timer(
                self._debounce_seconds,
                self._flush_session,
                kwargs={"session_id": session_id},
            )
            timer.daemon = True
            self._timers[session_id] = timer
            timer.start()

    def shutdown(self) -> None:
        """남아 있는 debounce timer와 세션 buffer를 정리한다."""

        with self._lock:
            timers = list(self._timers.values())
            self._timers.clear()
            self._buffers.clear()
            self._last_request_signatures.clear()

        for timer in timers:
            timer.cancel()

    def _flush_session(self, *, session_id: str) -> None:
        with self._lock:
            utterances = list(self._buffers.pop(session_id, ()))
            self._timers.pop(session_id, None)

        if not utterances:
            return

        selected_utterances = self._lane_filter.select_window(utterances)
        if not selected_utterances:
            return

        open_questions = self._state_store.list_open_questions(session_id)
        signature = build_window_signature(
            selected_utterances,
            [item.id for item in open_questions],
        )

        with self._lock:
            if self._last_request_signatures.get(session_id) == signature:
                logger.debug(
                    "실시간 질문 lane 중복 window 생략: session_id=%s",
                    session_id,
                )
                return
            self._last_request_signatures[session_id] = signature

        request = LiveQuestionRequest.create(
            session_id=session_id,
            utterances=selected_utterances,
            open_questions=open_questions,
        )
        self._queue.publish_request(request)
