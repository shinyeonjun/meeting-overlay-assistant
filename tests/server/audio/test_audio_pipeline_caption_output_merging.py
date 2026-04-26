from __future__ import annotations

from collections import deque

from server.app.domain.session import MeetingSession
from server.app.domain.shared.enums import AudioSource, SessionMode, SessionStatus
from server.app.infrastructure.persistence.postgresql.repositories.events import (
    PostgreSQLMeetingEventRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_utterance_repository import (
    PostgreSQLUtteranceRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.session import (
    PostgreSQLSessionRepository,
)
from server.app.services.audio.filters.transcription_guard import (
    TranscriptionGuard,
    TranscriptionGuardConfig,
)
from server.app.services.audio.pipeline.orchestrators.audio_pipeline_service import (
    AudioPipelineService,
)
from server.app.services.audio.segmentation.speech_segmenter import SpeechSegment
from server.app.services.audio.stt.transcription import TranscriptionResult
from server.app.services.events.meeting_event_service import MeetingEventService


class _NoOpAnalyzer:
    def analyze(self, utterance):
        return []


class _QueuedFinalSpeechToTextService:
    def __init__(self, texts: list[str]) -> None:
        self._texts = deque(texts)

    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        return TranscriptionResult(text=self._texts.popleft(), confidence=0.91)


class _SingleSegmentSequenceSegmenter:
    def __init__(self, *, segment_duration_ms: int = 400) -> None:
        self._cursor_ms = 0
        self._segment_duration_ms = segment_duration_ms

    def split(self, chunk: bytes) -> list[SpeechSegment]:
        if not chunk or chunk == b"silence":
            return []
        start_ms = self._cursor_ms
        end_ms = start_ms + self._segment_duration_ms
        self._cursor_ms = end_ms
        return [
            SpeechSegment(
                raw_bytes=chunk,
                start_ms=start_ms,
                end_ms=end_ms,
            )
        ]


def _save_session(database, session_id: str = "session-test") -> None:
    PostgreSQLSessionRepository(database).save(
        MeetingSession(
            id=session_id,
            title="자막 병합 테스트",
            mode=SessionMode.MEETING,
            primary_input_source=AudioSource.SYSTEM_AUDIO.value,
            status=SessionStatus.RUNNING,
            started_at="2025-01-01T00:00:00+00:00",
        )
    )


def test_짧은_비종결_final은_다음_final과_합쳐서_한줄로_전송한다(isolated_database):
    _save_session(isolated_database)
    pipeline = AudioPipelineService(
        segmenter=_SingleSegmentSequenceSegmenter(),
        speech_to_text_service=_QueuedFinalSpeechToTextService(
            [
                "도시에는 컴퓨터가",
                "있습니다.",
            ]
        ),
        analyzer_service=_NoOpAnalyzer(),
        utterance_repository=PostgreSQLUtteranceRepository(isolated_database),
        event_service=MeetingEventService(PostgreSQLMeetingEventRepository(isolated_database)),
        transcription_guard=TranscriptionGuard(TranscriptionGuardConfig()),
        transaction_manager=isolated_database,
    )
    now_ms = [600]
    pipeline._now_ms = lambda: now_ms[0]

    first_utterances, _ = pipeline.process_chunk(
        session_id="session-test",
        chunk=b"first",
    )
    now_ms[0] += 350
    second_utterances, _ = pipeline.process_chunk(
        session_id="session-test",
        chunk=b"second",
    )

    assert first_utterances == []
    assert len(second_utterances) == 1
    assert second_utterances[0].kind == "archive_final"
    assert second_utterances[0].text == "도시에는 컴퓨터가 있습니다."


def test_보류된_final은_후속_발화가_없어도_hold_시간이_지나면_전송한다(isolated_database):
    _save_session(isolated_database)
    pipeline = AudioPipelineService(
        segmenter=_SingleSegmentSequenceSegmenter(),
        speech_to_text_service=_QueuedFinalSpeechToTextService(["도시에는 컴퓨터가"]),
        analyzer_service=_NoOpAnalyzer(),
        utterance_repository=PostgreSQLUtteranceRepository(isolated_database),
        event_service=MeetingEventService(PostgreSQLMeetingEventRepository(isolated_database)),
        transcription_guard=TranscriptionGuard(TranscriptionGuardConfig()),
        transaction_manager=isolated_database,
    )
    now_ms = [600]
    pipeline._now_ms = lambda: now_ms[0]

    first_utterances, _ = pipeline.process_chunk(
        session_id="session-test",
        chunk=b"first",
    )
    now_ms[0] += 2_000
    second_utterances, _ = pipeline.process_chunk(
        session_id="session-test",
        chunk=b"silence",
    )

    assert first_utterances == []
    assert len(second_utterances) == 1
    assert second_utterances[0].kind == "archive_final"
    assert second_utterances[0].text == "도시에는 컴퓨터가"
