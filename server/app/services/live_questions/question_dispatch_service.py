"""실시간 질문 분석 요청 디스패처."""

from __future__ import annotations

import threading

from server.app.services.live_questions.models import LiveQuestionRequest, LiveQuestionUtterance


class NoOpLiveQuestionDispatchService:
    """질문 분석을 비활성화한 no-op 디스패처."""

    def submit(self, utterance) -> None:
        return None

    def shutdown(self) -> None:
        return None


class LiveQuestionDispatchService:
    """발화를 세션별로 묶어 질문 분석 요청으로 발행한다."""

    def __init__(
        self,
        *,
        queue,
        state_store,
        debounce_ms: int,
        window_size: int,
    ) -> None:
        self._queue = queue
        self._state_store = state_store
        self._debounce_seconds = max(debounce_ms, 0) / 1000
        self._window_size = max(window_size, 1)
        self._lock = threading.Lock()
        self._buffers: dict[str, list[LiveQuestionUtterance]] = {}
        self._timers: dict[str, threading.Timer] = {}

    def submit(self, utterance) -> None:
        """실시간 질문 분석 대상으로 발화를 등록한다."""

        snapshot = LiveQuestionUtterance.from_utterance(utterance)
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
        """남아 있는 타이머를 정리한다."""

        with self._lock:
            timers = list(self._timers.values())
            self._timers.clear()
            self._buffers.clear()

        for timer in timers:
            timer.cancel()

    def _flush_session(self, *, session_id: str) -> None:
        with self._lock:
            utterances = list(self._buffers.pop(session_id, ()))
            self._timers.pop(session_id, None)

        if not utterances:
            return

        request = LiveQuestionRequest.create(
            session_id=session_id,
            utterances=utterances,
            open_questions=self._state_store.list_open_questions(session_id),
        )
        self._queue.publish_request(request)
