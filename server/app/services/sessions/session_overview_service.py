"""세션 영역의 session overview service 서비스를 제공한다."""
from __future__ import annotations

from server.app.repositories.contracts.meeting_event_repository import MeetingEventRepository
from server.app.repositories.contracts.session import SessionRepository
from server.app.repositories.contracts.utterance_repository import UtteranceRepository
from server.app.services.analysis.observability import get_insight_metrics_snapshot
from server.app.services.sessions.overview_builder import SessionOverview, SessionOverviewBuilder
from server.app.services.sessions.topic_summarizer import TopicSummarizer


class SessionOverviewService:
    """세션과 이벤트, 최근 발화를 묶어 overview를 생성한다."""

    def __init__(
        self,
        session_repository: SessionRepository,
        event_repository: MeetingEventRepository,
        utterance_repository: UtteranceRepository,
        overview_builder: SessionOverviewBuilder,
        topic_summarizer: TopicSummarizer,
        recent_topic_utterance_count: int = 5,
        min_topic_utterance_length: int = 10,
        min_topic_utterance_confidence: float = 0.58,
        recent_metrics_utterance_count: int = 50,
    ) -> None:
        self._session_repository = session_repository
        self._event_repository = event_repository
        self._utterance_repository = utterance_repository
        self._overview_builder = overview_builder
        self._topic_summarizer = topic_summarizer
        self._recent_topic_utterance_count = recent_topic_utterance_count
        self._min_topic_utterance_length = min_topic_utterance_length
        self._min_topic_utterance_confidence = min_topic_utterance_confidence
        self._recent_metrics_utterance_count = recent_metrics_utterance_count

    def build_overview(self, session_id: str) -> SessionOverview:
        """세션 overview를 생성한다."""
        session = self._session_repository.get_by_id(session_id)
        if session is None:
            raise ValueError(f"존재하지 않는 세션입니다: {session_id}")

        events = self._event_repository.list_by_session(session_id)
        overview = self._overview_builder.build(session=session, events=events)
        topic_texts = self._collect_topic_candidate_texts(session_id)
        summarized_topic = self._topic_summarizer.summarize(
            session_id=session_id,
            topic_texts=topic_texts,
            fallback_topic=overview.current_topic,
        )
        recent_utterances = self._utterance_repository.list_recent_by_session(
            session_id,
            self._recent_metrics_utterance_count,
        )
        recent_average_latency_ms = self._calculate_average_latency(recent_utterances)
        recent_utterance_count_by_source = self._count_utterances_by_source(recent_utterances)
        return SessionOverview(
            session=overview.session,
            current_topic=summarized_topic,
            questions=overview.questions,
            decisions=overview.decisions,
            action_items=overview.action_items,
            risks=overview.risks,
            recent_average_latency_ms=recent_average_latency_ms,
            recent_utterance_count_by_source=recent_utterance_count_by_source,
            insight_metrics=get_insight_metrics_snapshot(),
        )

    def _collect_topic_candidate_texts(self, session_id: str) -> list[str]:
        recent_utterances = self._utterance_repository.list_recent_by_session(
            session_id,
            self._recent_topic_utterance_count,
        )
        return [
            utterance.text.strip()
            for utterance in recent_utterances
            if len(utterance.text.strip()) >= self._min_topic_utterance_length
            and utterance.confidence >= self._min_topic_utterance_confidence
        ]

    @staticmethod
    def _calculate_average_latency(utterances) -> float | None:
        latencies = [
            utterance.latency_ms
            for utterance in utterances
            if utterance.latency_ms is not None and utterance.latency_ms >= 0
        ]
        if not latencies:
            return None
        return round(sum(latencies) / len(latencies), 2)

    @staticmethod
    def _count_utterances_by_source(utterances) -> dict[str, int]:
        counts: dict[str, int] = {}
        for utterance in utterances:
            source = (utterance.input_source or "unknown").strip() or "unknown"
            counts[source] = counts.get(source, 0) + 1
        return counts
