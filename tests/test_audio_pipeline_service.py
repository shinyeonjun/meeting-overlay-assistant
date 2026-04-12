"""오디오 파이프라인 테스트."""

from __future__ import annotations

import logging

from backend.app.domain.models.session import MeetingSession
from backend.app.domain.models.meeting_event import MeetingEvent
from backend.app.domain.shared.enums import (
    AudioSource,
    EventPriority,
    EventState,
    EventType,
    SessionMode,
    SessionStatus,
)
from backend.app.infrastructure.persistence.sqlite.repositories.meeting_event_repository import (
    SQLiteMeetingEventRepository,
)
from backend.app.infrastructure.persistence.sqlite.repositories.session_repository import (
    SQLiteSessionRepository,
)
from backend.app.infrastructure.persistence.sqlite.repositories.utterance_repository import (
    SQLiteUtteranceRepository,
)
from backend.app.services.analysis.analyzers.rule_based_meeting_analyzer import (
    RuleBasedMeetingAnalyzer,
)
from backend.app.services.audio.pipeline.audio_pipeline_service import AudioPipelineService
from backend.app.services.audio.pipeline.live_stream_utterance import LiveStreamUtterance
from backend.app.services.audio.stt.placeholder_speech_to_text_service import (
    PlaceholderSpeechToTextService,
)
from backend.app.services.audio.segmentation.speech_segmenter import SpeechSegment, SpeechSegmenter
from backend.app.services.audio.stt.transcription import TranscriptionResult
from backend.app.services.audio.filters.transcription_guard import (
    TranscriptionGuard,
    TranscriptionGuardConfig,
)
from backend.app.services.events.meeting_event_service import MeetingEventService
from tests.support.sample_inputs import ACTION_TEXT, QUESTION_TEXT, RISK_TEXT


class _EmptySpeechToTextService:
    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        return TranscriptionResult(text="", confidence=0.0)


class _FixedSpeechToTextService:
    def __init__(self, text: str, confidence: float) -> None:
        self._text = text
        self._confidence = confidence

    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        return TranscriptionResult(text=self._text, confidence=self._confidence)


class _FixedSpeechToTextServiceWithNoSpeechProb:
    def __init__(self, text: str, confidence: float, no_speech_prob: float) -> None:
        self._text = text
        self._confidence = confidence
        self._no_speech_prob = no_speech_prob

    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        return TranscriptionResult(
            text=self._text,
            confidence=self._confidence,
            no_speech_prob=self._no_speech_prob,
        )


class _StreamingSpeechToTextService:
    def __init__(self) -> None:
        self._preview_revision = 0

    def preview_chunk(self, chunk: bytes) -> list[TranscriptionResult]:
        self._preview_revision += 1
        return [
            TranscriptionResult(
                text="실시간 partial",
                confidence=0.72,
                kind="partial",
                revision=self._preview_revision,
            )
        ]

    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        return TranscriptionResult(text="", confidence=0.0)

    def reset_stream(self) -> None:
        self._preview_revision = 0


class _StreamingSpeechToTextServiceWithFinal:
    def __init__(self) -> None:
        self._preview_revision = 0

    def preview_chunk(self, chunk: bytes) -> list[TranscriptionResult]:
        self._preview_revision += 1
        return [
            TranscriptionResult(
                text=f"partial-{self._preview_revision}",
                confidence=0.82,
                kind="partial",
                revision=self._preview_revision,
            )
        ]

    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        return TranscriptionResult(text="확정 문장", confidence=0.91)

    def reset_stream(self) -> None:
        self._preview_revision = 0


class _CountingStreamingSpeechToTextServiceWithFinal:
    def __init__(self) -> None:
        self._preview_revision = 0
        self.preview_call_count = 0

    def preview_chunk(self, chunk: bytes) -> list[TranscriptionResult]:
        self.preview_call_count += 1
        self._preview_revision += 1
        return [
            TranscriptionResult(
                text=f"partial-{self._preview_revision}",
                confidence=0.82,
                kind="partial",
                revision=self._preview_revision,
            )
        ]

    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        return TranscriptionResult(text="확정 문장", confidence=0.91)

    def reset_stream(self) -> None:
        self._preview_revision = 0


class _FinalOnlySpeechToTextService:
    def preview_chunk(self, chunk: bytes) -> list[TranscriptionResult]:
        return []

    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        return TranscriptionResult(text="늦게 도착한 확정 문장", confidence=0.91)

    def reset_stream(self) -> None:
        return None


class _SingleCharStreamingSpeechToTextService:
    def preview_chunk(self, chunk: bytes) -> list[TranscriptionResult]:
        return [
            TranscriptionResult(
                text="아",
                confidence=0.82,
                kind="partial",
                revision=1,
            )
        ]

    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        return TranscriptionResult(text="", confidence=0.0)

    def reset_stream(self) -> None:
        return None


class _BlockedPreviewStreamingSpeechToTextService:
    def preview_chunk(self, chunk: bytes) -> list[TranscriptionResult]:
        return [
            TranscriptionResult(
                text="다음 영상에서 만나요",
                confidence=0.62,
                kind="partial",
                revision=1,
                no_speech_prob=0.92,
            )
        ]

    def transcribe(self, segment: SpeechSegment) -> TranscriptionResult:
        return TranscriptionResult(text="", confidence=0.0)

    def reset_stream(self) -> None:
        return None


class _EarlyEouHintSegmenter:
    def __init__(self) -> None:
        self._pending_hint = True

    def split(self, chunk: bytes) -> list[SpeechSegment]:
        return []

    def consume_early_eou_hint(self) -> bool:
        if not self._pending_hint:
            return False
        self._pending_hint = False
        return True


class _OldSegmenter:
    def split(self, chunk: bytes) -> list[SpeechSegment]:
        return [
            SpeechSegment(
                raw_bytes=chunk,
                start_ms=1_000,
                end_ms=2_000,
            )
        ]


class _NoOpAnalyzer:
    def analyze(self, utterance):
        return []


class _DuplicateQuestionAnalyzer:
    def analyze(self, utterance):
        return [
            MeetingEvent.create(
                session_id=utterance.session_id,
                event_type=EventType.QUESTION,
                title=utterance.text,
                state=EventState.OPEN,
                priority=EventPriority.QUESTION,
                source_utterance_id=utterance.id,
                evidence_text=utterance.text,
                input_source=utterance.input_source,
            ),
            MeetingEvent.create(
                session_id=utterance.session_id,
                event_type=EventType.QUESTION,
                title="질문 확인 필요",
                state=EventState.OPEN,
                priority=EventPriority.QUESTION,
                source_utterance_id=utterance.id,
                evidence_text=utterance.text,
                input_source=utterance.input_source,
            ),
        ]


class _MixedLiveAnalyzer:
    def analyze(self, utterance):
        return [
            MeetingEvent.create(
                session_id=utterance.session_id,
                event_type=EventType.QUESTION,
                title="질문 하나",
                state=EventState.OPEN,
                priority=EventPriority.QUESTION,
                source_utterance_id=utterance.id,
                evidence_text=utterance.text,
                input_source=utterance.input_source,
            ),
            MeetingEvent.create(
                session_id=utterance.session_id,
                event_type=EventType.DECISION,
                title="결정 하나",
                state=EventState.CONFIRMED,
                priority=EventPriority.DECISION,
                source_utterance_id=utterance.id,
                evidence_text=utterance.text,
                input_source=utterance.input_source,
            ),
            MeetingEvent.create(
                session_id=utterance.session_id,
                event_type=EventType.ACTION_ITEM,
                title="액션 하나",
                state=EventState.CANDIDATE,
                priority=EventPriority.ACTION_ITEM,
                source_utterance_id=utterance.id,
                evidence_text=utterance.text,
                input_source=utterance.input_source,
            ),
        ]


class _FailingAnalyzer:
    def analyze(self, utterance):
        raise RuntimeError("분석 실패")


class TestAudioPipelineService:
    """오디오 파이프라인 동작을 검증한다."""

    @staticmethod
    def _save_session(database, session_id: str = "session-test") -> None:
        repository = SQLiteSessionRepository(database)
        repository.save(
            MeetingSession(
                id=session_id,
                title="테스트 회의",
                mode=SessionMode.MEETING,
                source=AudioSource.SYSTEM_AUDIO,
                status=SessionStatus.RUNNING,
                started_at="2025-01-01T00:00:00+00:00",
            )
        )

    def test_텍스트_chunk를_처리하면_live에서는_질문이_아닌_이벤트를_저장하지_않는다(self, isolated_database):
        self._save_session(isolated_database)
        event_repository = SQLiteMeetingEventRepository(isolated_database)
        pipeline = AudioPipelineService(
            segmenter=SpeechSegmenter(),
            speech_to_text_service=PlaceholderSpeechToTextService(),
            analyzer_service=RuleBasedMeetingAnalyzer(),
            utterance_repository=SQLiteUtteranceRepository(isolated_database),
            event_service=MeetingEventService(event_repository),
            transcription_guard=TranscriptionGuard(TranscriptionGuardConfig()),
            transaction_manager=isolated_database,
        )

        utterances, events = pipeline.process_chunk(
            session_id="session-test",
            chunk=ACTION_TEXT.encode("utf-8"),
        )

        assert len(utterances) == 1
        assert utterances[0].text == ACTION_TEXT
        assert events == []
        assert event_repository.list_by_session("session-test") == []

    def test_같은_발화의_동일_event_type은_한건으로_병합된다(self, isolated_database):
        self._save_session(isolated_database)
        event_repository = SQLiteMeetingEventRepository(isolated_database)
        pipeline = AudioPipelineService(
            segmenter=SpeechSegmenter(),
            speech_to_text_service=PlaceholderSpeechToTextService(),
            analyzer_service=_DuplicateQuestionAnalyzer(),
            utterance_repository=SQLiteUtteranceRepository(isolated_database),
            event_service=MeetingEventService(event_repository),
            transcription_guard=TranscriptionGuard(TranscriptionGuardConfig()),
            transaction_manager=isolated_database,
        )

        _utterances, events = pipeline.process_chunk(
            session_id="session-test",
            chunk=QUESTION_TEXT.encode("utf-8"),
        )
        saved_events = event_repository.list_by_session("session-test")

        assert len(events) == 1
        assert len(saved_events) == 1
        assert events[0].event_type == EventType.QUESTION
        assert events[0].title == "질문 확인 필요"

    def test_live_이벤트는_질문만_저장한다(self, isolated_database):
        self._save_session(isolated_database)
        event_repository = SQLiteMeetingEventRepository(isolated_database)
        pipeline = AudioPipelineService(
            segmenter=SpeechSegmenter(),
            speech_to_text_service=PlaceholderSpeechToTextService(),
            analyzer_service=_MixedLiveAnalyzer(),
            utterance_repository=SQLiteUtteranceRepository(isolated_database),
            event_service=MeetingEventService(event_repository),
            transcription_guard=TranscriptionGuard(TranscriptionGuardConfig()),
            transaction_manager=isolated_database,
        )

        _utterances, events = pipeline.process_chunk(
            session_id="session-test",
            chunk=QUESTION_TEXT.encode("utf-8"),
        )
        saved_events = event_repository.list_by_session("session-test")

        assert len(events) == 1
        assert len(saved_events) == 1
        assert events[0].event_type == EventType.QUESTION
        assert saved_events[0].event_type == EventType.QUESTION

    def test_early_eou_힌트가_있으면_partial_preview를_fast_final로_승격한다(self, isolated_database):
        self._save_session(isolated_database)
        pipeline = AudioPipelineService(
            segmenter=_EarlyEouHintSegmenter(),
            speech_to_text_service=_StreamingSpeechToTextService(),
            analyzer_service=_NoOpAnalyzer(),
            utterance_repository=SQLiteUtteranceRepository(isolated_database),
            event_service=MeetingEventService(SQLiteMeetingEventRepository(isolated_database)),
            transcription_guard=TranscriptionGuard(TranscriptionGuardConfig()),
            transaction_manager=isolated_database,
        )

        utterances, events = pipeline.process_chunk(
            session_id="session-test",
            chunk=b"preview-only",
            input_source=AudioSource.SYSTEM_AUDIO.value,
        )

        assert events == []
        assert len(utterances) == 1
        assert isinstance(utterances[0], LiveStreamUtterance)
        assert utterances[0].kind == "fast_final"
        assert utterances[0].stability == "medium"

    def test_빈_전사는_utterance와_event를_저장하지_않는다(self, isolated_database):
        self._save_session(isolated_database)
        event_repository = SQLiteMeetingEventRepository(isolated_database)
        utterance_repository = SQLiteUtteranceRepository(isolated_database)
        pipeline = AudioPipelineService(
            segmenter=SpeechSegmenter(),
            speech_to_text_service=_EmptySpeechToTextService(),
            analyzer_service=RuleBasedMeetingAnalyzer(),
            utterance_repository=utterance_repository,
            event_service=MeetingEventService(event_repository),
            transcription_guard=TranscriptionGuard(TranscriptionGuardConfig()),
            transaction_manager=isolated_database,
        )

        utterances, events = pipeline.process_chunk(
            session_id="session-test",
            chunk=b"\x00\x00" * 16000,
        )

        assert utterances == []
        assert events == []
        assert utterance_repository.list_by_session("session-test") == []

    def test_같은_질문을_두번_입력하면_이벤트를_중복_생성하지_않고_갱신한다(self, isolated_database):
        self._save_session(isolated_database)
        event_repository = SQLiteMeetingEventRepository(isolated_database)
        pipeline = AudioPipelineService(
            segmenter=SpeechSegmenter(),
            speech_to_text_service=PlaceholderSpeechToTextService(),
            analyzer_service=RuleBasedMeetingAnalyzer(),
            utterance_repository=SQLiteUtteranceRepository(isolated_database),
            event_service=MeetingEventService(event_repository),
            transcription_guard=TranscriptionGuard(TranscriptionGuardConfig()),
            transaction_manager=isolated_database,
        )

        _, first_events = pipeline.process_chunk(
            session_id="session-test",
            chunk=QUESTION_TEXT.encode("utf-8"),
        )
        _, second_events = pipeline.process_chunk(
            session_id="session-test",
            chunk=QUESTION_TEXT.encode("utf-8"),
        )

        saved_events = event_repository.list_by_session("session-test")

        assert len(first_events) == 1
        assert len(second_events) == 1
        assert first_events[0].id == second_events[0].id
        assert len(saved_events) == 1

    def test_같은_리스크를_두번_입력해도_live에서는_저장하지_않는다(self, isolated_database):
        self._save_session(isolated_database)
        event_repository = SQLiteMeetingEventRepository(isolated_database)
        pipeline = AudioPipelineService(
            segmenter=SpeechSegmenter(),
            speech_to_text_service=PlaceholderSpeechToTextService(),
            analyzer_service=RuleBasedMeetingAnalyzer(),
            utterance_repository=SQLiteUtteranceRepository(isolated_database),
            event_service=MeetingEventService(event_repository),
            transcription_guard=TranscriptionGuard(TranscriptionGuardConfig()),
            transaction_manager=isolated_database,
        )

        _, first_events = pipeline.process_chunk(
            session_id="session-test",
            chunk=RISK_TEXT.encode("utf-8"),
        )
        _, second_events = pipeline.process_chunk(
            session_id="session-test",
            chunk=RISK_TEXT.encode("utf-8"),
        )

        saved_events = event_repository.list_by_session("session-test")
        risk_events = [event for event in saved_events if event.event_type == EventType.RISK]

        assert first_events == []
        assert second_events == []
        assert len(risk_events) == 0

    def test_세그먼트_처리_중_예외가_나면_저장한_발화가_롤백된다(self, isolated_database):
        self._save_session(isolated_database)
        utterance_repository = SQLiteUtteranceRepository(isolated_database)
        event_repository = SQLiteMeetingEventRepository(isolated_database)
        pipeline = AudioPipelineService(
            segmenter=SpeechSegmenter(),
            speech_to_text_service=PlaceholderSpeechToTextService(),
            analyzer_service=_FailingAnalyzer(),
            utterance_repository=utterance_repository,
            event_service=MeetingEventService(event_repository),
            transcription_guard=TranscriptionGuard(TranscriptionGuardConfig()),
            transaction_manager=isolated_database,
        )

        try:
            pipeline.process_chunk(
                session_id="session-test",
                chunk=QUESTION_TEXT.encode("utf-8"),
            )
            assert False, "예외가 발생해야 한다."
        except RuntimeError as error:
            assert str(error) == "분석 실패"

        assert utterance_repository.list_by_session("session-test") == []

    def test_낮은_confidence의_인접_중복_전사는_저장하지_않는다(self, isolated_database):
        self._save_session(isolated_database)
        utterance_repository = SQLiteUtteranceRepository(isolated_database)
        event_repository = SQLiteMeetingEventRepository(isolated_database)
        pipeline = AudioPipelineService(
            segmenter=SpeechSegmenter(),
            speech_to_text_service=_FixedSpeechToTextService(
                text="다음 영상에서 만나요.",
                confidence=0.62,
            ),
            analyzer_service=RuleBasedMeetingAnalyzer(),
            utterance_repository=utterance_repository,
            event_service=MeetingEventService(event_repository),
            transcription_guard=TranscriptionGuard(
                TranscriptionGuardConfig(
                    min_confidence=0.35,
                    blocked_phrases=(),
                    blocked_phrase_max_confidence=0.8,
                )
            ),
            transaction_manager=isolated_database,
            duplicate_window_ms=10000,
            duplicate_similarity_threshold=0.9,
            duplicate_max_confidence=0.8,
        )

        first_utterances, _ = pipeline.process_chunk(
            session_id="session-test",
            chunk=b"first",
        )
        second_utterances, second_events = pipeline.process_chunk(
            session_id="session-test",
            chunk=b"second",
        )

        saved_utterances = utterance_repository.list_by_session("session-test")

        assert len(first_utterances) == 1
        assert second_utterances == []
        assert second_events == []
        assert len(saved_utterances) == 1

    def test_streaming_partial은_live_payload로만_반환하고_DB에는_저장하지_않는다(self, isolated_database):
        self._save_session(isolated_database)
        utterance_repository = SQLiteUtteranceRepository(isolated_database)
        event_repository = SQLiteMeetingEventRepository(isolated_database)
        pipeline = AudioPipelineService(
            segmenter=SpeechSegmenter(),
            speech_to_text_service=_StreamingSpeechToTextService(),
            analyzer_service=RuleBasedMeetingAnalyzer(),
            utterance_repository=utterance_repository,
            event_service=MeetingEventService(event_repository),
            transcription_guard=TranscriptionGuard(TranscriptionGuardConfig()),
            transaction_manager=isolated_database,
        )

        utterances, events = pipeline.process_chunk(
            session_id="session-test",
            chunk=b"partial only",
        )

        assert len(utterances) == 1
        assert isinstance(utterances[0], LiveStreamUtterance)
        assert utterances[0].kind == "partial"
        assert events == []
        assert utterance_repository.list_by_session("session-test") == []

    def test_streaming_partial_revision은_같은_active_slot_seq를_재사용한다(self, isolated_database):
        self._save_session(isolated_database)
        pipeline = AudioPipelineService(
            segmenter=SpeechSegmenter(),
            speech_to_text_service=_StreamingSpeechToTextService(),
            analyzer_service=RuleBasedMeetingAnalyzer(),
            utterance_repository=SQLiteUtteranceRepository(isolated_database),
            event_service=MeetingEventService(SQLiteMeetingEventRepository(isolated_database)),
            transcription_guard=TranscriptionGuard(TranscriptionGuardConfig()),
            transaction_manager=isolated_database,
        )

        first_utterances, _ = pipeline.process_chunk(
            session_id="session-test",
            chunk=b"partial-1",
        )
        second_utterances, _ = pipeline.process_chunk(
            session_id="session-test",
            chunk=b"partial-2",
        )

        assert len(first_utterances) == 1
        assert len(second_utterances) == 1
        assert isinstance(first_utterances[0], LiveStreamUtterance)
        assert isinstance(second_utterances[0], LiveStreamUtterance)
        assert first_utterances[0].seq_num == second_utterances[0].seq_num
        assert first_utterances[0].segment_id == second_utterances[0].segment_id
        assert first_utterances[0].revision == 1
        assert second_utterances[0].revision == 2

    def test_한_글자_partial은_preview_min_compact_length로_숨긴다(self, isolated_database):
        self._save_session(isolated_database)
        pipeline = AudioPipelineService(
            segmenter=SpeechSegmenter(),
            speech_to_text_service=_SingleCharStreamingSpeechToTextService(),
            analyzer_service=RuleBasedMeetingAnalyzer(),
            utterance_repository=SQLiteUtteranceRepository(isolated_database),
            event_service=MeetingEventService(SQLiteMeetingEventRepository(isolated_database)),
            transcription_guard=TranscriptionGuard(TranscriptionGuardConfig()),
            transaction_manager=isolated_database,
            preview_min_compact_length=10,
        )

        utterances, events = pipeline.process_chunk(
            session_id="session-test",
            chunk=b"partial-too-short",
        )

        assert utterances == []
        assert events == []

    def test_same_chunk에서_final이_생기면_partial_payload는_숨긴다(self, isolated_database):
        self._save_session(isolated_database)
        utterance_repository = SQLiteUtteranceRepository(isolated_database)
        pipeline = AudioPipelineService(
            segmenter=SpeechSegmenter(),
            speech_to_text_service=_StreamingSpeechToTextServiceWithFinal(),
            analyzer_service=_NoOpAnalyzer(),
            utterance_repository=utterance_repository,
            event_service=MeetingEventService(SQLiteMeetingEventRepository(isolated_database)),
            transcription_guard=TranscriptionGuard(TranscriptionGuardConfig()),
            transaction_manager=isolated_database,
        )

        utterances, events = pipeline.process_chunk(
            session_id="session-test",
            chunk=b"partial-and-final",
        )

        assert len(utterances) == 1
        assert utterances[0].text == "확정 문장"
        assert isinstance(utterances[0], LiveStreamUtterance)
        assert utterances[0].segment_id.startswith("seg-live-")
        assert utterances[0].seq_num == 1
        assert events == []
        saved = utterance_repository.list_by_session("session-test")
        assert len(saved) == 1

    def test_짧은_final은_confidence가_낮으면_추가로_걸러낸다(self, isolated_database):
        self._save_session(isolated_database)
        utterance_repository = SQLiteUtteranceRepository(isolated_database)
        pipeline = AudioPipelineService(
            segmenter=SpeechSegmenter(),
            speech_to_text_service=_FixedSpeechToTextService(
                text="감사합니다",
                confidence=0.41,
            ),
            analyzer_service=_NoOpAnalyzer(),
            utterance_repository=utterance_repository,
            event_service=MeetingEventService(SQLiteMeetingEventRepository(isolated_database)),
            transcription_guard=TranscriptionGuard(
                TranscriptionGuardConfig(
                    min_confidence=0.35,
                    short_text_min_confidence=0.35,
                )
            ),
            transaction_manager=isolated_database,
            final_short_text_max_compact_length=5,
            final_short_text_min_confidence=0.58,
        )

        utterances, events = pipeline.process_chunk(
            session_id="session-test",
            chunk=b"short-final",
        )

        assert utterances == []
        assert events == []
        assert utterance_repository.list_by_session("session-test") == []

    def test_no_speech_prob_차단_사유를_로그로_남긴다(self, isolated_database, caplog):
        self._save_session(isolated_database)
        event_repository = SQLiteMeetingEventRepository(isolated_database)
        pipeline = AudioPipelineService(
            segmenter=SpeechSegmenter(),
            speech_to_text_service=_FixedSpeechToTextServiceWithNoSpeechProb(
                text="감사합니다",
                confidence=0.78,
                no_speech_prob=0.91,
            ),
            analyzer_service=RuleBasedMeetingAnalyzer(),
            utterance_repository=SQLiteUtteranceRepository(isolated_database),
            event_service=MeetingEventService(event_repository),
            transcription_guard=TranscriptionGuard(
                TranscriptionGuardConfig(
                    min_confidence=0.35,
                    max_no_speech_prob=0.8,
                )
            ),
            transaction_manager=isolated_database,
        )

        with caplog.at_level(logging.INFO):
            utterances, events = pipeline.process_chunk(
                session_id="session-test",
                chunk=b"fake-audio",
            )

        assert utterances == []
        assert events == []
        assert "reason=high_no_speech_prob" in caplog.text

    def test_partial_환각_문구도_가드에서_차단한다(self, isolated_database, caplog):
        self._save_session(isolated_database)
        utterance_repository = SQLiteUtteranceRepository(isolated_database)
        event_repository = SQLiteMeetingEventRepository(isolated_database)
        pipeline = AudioPipelineService(
            segmenter=SpeechSegmenter(),
            speech_to_text_service=_BlockedPreviewStreamingSpeechToTextService(),
            analyzer_service=RuleBasedMeetingAnalyzer(),
            utterance_repository=utterance_repository,
            event_service=MeetingEventService(event_repository),
            transcription_guard=TranscriptionGuard(
                TranscriptionGuardConfig(
                    min_confidence=0.35,
                    blocked_phrases=("다음 영상에서 만나요",),
                    blocked_phrase_max_confidence=0.8,
                    max_no_speech_prob=0.8,
                )
            ),
            transaction_manager=isolated_database,
        )

        with caplog.at_level(logging.INFO):
            utterances, events = pipeline.process_chunk(
                session_id="session-test",
                chunk=b"partial only",
            )

        assert utterances == []
        assert events == []
        assert utterance_repository.list_by_session("session-test") == []
        assert "partial 전사 필터링" in caplog.text

    def test_final_queue_delay가_크면_partial_backpressure를_활성화한다(self, isolated_database, caplog):
        self._save_session(isolated_database)
        pipeline = AudioPipelineService(
            segmenter=_OldSegmenter(),
            speech_to_text_service=_StreamingSpeechToTextServiceWithFinal(),
            analyzer_service=_NoOpAnalyzer(),
            utterance_repository=SQLiteUtteranceRepository(isolated_database),
            event_service=MeetingEventService(SQLiteMeetingEventRepository(isolated_database)),
            transcription_guard=TranscriptionGuard(TranscriptionGuardConfig()),
            transaction_manager=isolated_database,
            preview_backpressure_queue_delay_ms=100,
            preview_backpressure_hold_chunks=2,
        )

        with caplog.at_level(logging.INFO):
            first_utterances, _ = pipeline.process_chunk(
                session_id="session-test",
                chunk=b"first",
            )
            second_utterances, _ = pipeline.process_chunk(
                session_id="session-test",
                chunk=b"second",
            )

        assert len(first_utterances) == 1
        assert first_utterances[0].kind == "final"
        assert len(second_utterances) == 1
        assert second_utterances[0].kind == "final"
        assert "preview backpressure 활성화" in caplog.text
        assert "partial 전사 억제: reason=backpressure" in caplog.text

    def test_backpressure_중에는_preview_transcribe를_호출하지_않는다(self, isolated_database, caplog):
        self._save_session(isolated_database)
        speech_to_text_service = _CountingStreamingSpeechToTextServiceWithFinal()
        pipeline = AudioPipelineService(
            segmenter=_OldSegmenter(),
            speech_to_text_service=speech_to_text_service,
            analyzer_service=_NoOpAnalyzer(),
            utterance_repository=SQLiteUtteranceRepository(isolated_database),
            event_service=MeetingEventService(SQLiteMeetingEventRepository(isolated_database)),
            transcription_guard=TranscriptionGuard(TranscriptionGuardConfig()),
            transaction_manager=isolated_database,
            preview_backpressure_queue_delay_ms=100,
            preview_backpressure_hold_chunks=2,
        )

        with caplog.at_level(logging.INFO):
            pipeline.process_chunk(
                session_id="session-test",
                chunk=b"first",
            )
            pipeline.process_chunk(
                session_id="session-test",
                chunk=b"second",
            )

        assert speech_to_text_service.preview_call_count == 1
        assert "partial 전사 억제: reason=backpressure" in caplog.text

    def test_늦게_도착한_final은_live_payload로_내보내지_않는다(self, isolated_database, caplog):
        self._save_session(isolated_database)
        utterance_repository = SQLiteUtteranceRepository(isolated_database)
        pipeline = AudioPipelineService(
            segmenter=_OldSegmenter(),
            speech_to_text_service=_StreamingSpeechToTextServiceWithFinal(),
            analyzer_service=_NoOpAnalyzer(),
            utterance_repository=utterance_repository,
            event_service=MeetingEventService(SQLiteMeetingEventRepository(isolated_database)),
            transcription_guard=TranscriptionGuard(TranscriptionGuardConfig()),
            transaction_manager=isolated_database,
            live_final_emit_max_delay_ms=100,
        )

        with caplog.at_level(logging.INFO):
            utterances, events = pipeline.process_chunk(
                session_id="session-test",
                chunk=b"late-final",
            )

        assert len(utterances) == 1
        assert utterances[0].kind == "partial"
        assert utterances[0].text == "partial-1"
        assert events == []
        saved = utterance_repository.list_by_session("session-test")
        assert len(saved) == 1
        assert saved[0].text == "확정 문장"
        assert "live final 전송 생략" in caplog.text

    def test_늦게_도착한_final은_preview_backpressure를_걸지_않는다(self, isolated_database, caplog):
        self._save_session(isolated_database)
        speech_to_text_service = _CountingStreamingSpeechToTextServiceWithFinal()
        pipeline = AudioPipelineService(
            segmenter=_OldSegmenter(),
            speech_to_text_service=speech_to_text_service,
            analyzer_service=_NoOpAnalyzer(),
            utterance_repository=SQLiteUtteranceRepository(isolated_database),
            event_service=MeetingEventService(SQLiteMeetingEventRepository(isolated_database)),
            transcription_guard=TranscriptionGuard(TranscriptionGuardConfig()),
            transaction_manager=isolated_database,
            preview_backpressure_queue_delay_ms=100,
            preview_backpressure_hold_chunks=2,
            live_final_emit_max_delay_ms=100,
        )

        with caplog.at_level(logging.INFO):
            first_utterances, _ = pipeline.process_chunk(
                session_id="session-test",
                chunk=b"first",
            )
            second_utterances, _ = pipeline.process_chunk(
                session_id="session-test",
                chunk=b"second",
            )

        assert len(first_utterances) == 1
        assert first_utterances[0].kind == "partial"
        assert len(second_utterances) == 1
        assert second_utterances[0].kind == "partial"
        assert speech_to_text_service.preview_call_count == 2
        assert "live final 전송 생략" in caplog.text
        assert "partial 전사 억제: reason=backpressure" not in caplog.text

    def test_초기_grace_구간에서는_늦은_final도_live로_전송한다(self, isolated_database):
        self._save_session(isolated_database)
        pipeline = AudioPipelineService(
            segmenter=_OldSegmenter(),
            speech_to_text_service=_FinalOnlySpeechToTextService(),
            analyzer_service=_NoOpAnalyzer(),
            utterance_repository=SQLiteUtteranceRepository(isolated_database),
            event_service=MeetingEventService(SQLiteMeetingEventRepository(isolated_database)),
            transcription_guard=TranscriptionGuard(TranscriptionGuardConfig()),
            transaction_manager=isolated_database,
            live_final_emit_max_delay_ms=3_500,
            live_final_initial_grace_segments=3,
            live_final_initial_grace_delay_ms=6_000,
        )
        pipeline._now_ms = lambda: 7_000

        utterances, events = pipeline.process_chunk(
            session_id="session-test",
            chunk=b"late-final-with-grace",
        )

        assert events == []
        assert len(utterances) == 1
        assert utterances[0].kind == "final"
        assert utterances[0].text == "늦게 도착한 확정 문장"

    def test_초기_grace_구간이_끝나면_다시_늦은_final을_생략한다(self, isolated_database):
        self._save_session(isolated_database)
        pipeline = AudioPipelineService(
            segmenter=_OldSegmenter(),
            speech_to_text_service=_FinalOnlySpeechToTextService(),
            analyzer_service=_NoOpAnalyzer(),
            utterance_repository=SQLiteUtteranceRepository(isolated_database),
            event_service=MeetingEventService(SQLiteMeetingEventRepository(isolated_database)),
            transcription_guard=TranscriptionGuard(TranscriptionGuardConfig()),
            transaction_manager=isolated_database,
            live_final_emit_max_delay_ms=3_500,
            live_final_initial_grace_segments=1,
            live_final_initial_grace_delay_ms=6_000,
        )
        pipeline._now_ms = lambda: 7_000

        first_utterances, _ = pipeline.process_chunk(
            session_id="session-test",
            chunk=b"first-grace-final",
        )
        second_utterances, _ = pipeline.process_chunk(
            session_id="session-test",
            chunk=b"second-late-final",
        )

        assert len(first_utterances) == 1
        assert first_utterances[0].kind == "final"
        assert second_utterances == []

    def test_최근_preview가_있으면_grace_matching으로_same_segment_final을_묶는다(self, isolated_database):
        self._save_session(isolated_database)
        pipeline = AudioPipelineService(
            segmenter=_OldSegmenter(),
            speech_to_text_service=_FinalOnlySpeechToTextService(),
            analyzer_service=_NoOpAnalyzer(),
            utterance_repository=SQLiteUtteranceRepository(isolated_database),
            event_service=MeetingEventService(SQLiteMeetingEventRepository(isolated_database)),
            transcription_guard=TranscriptionGuard(TranscriptionGuardConfig()),
            transaction_manager=isolated_database,
            segment_grace_match_max_gap_ms=1_500,
        )
        pipeline._alignment_manager.prime_recent_preview_for_test(
            seq_num=7,
            segment_id="seg-live-7",
            seen_at_ms=pipeline._now_ms(),
        )

        utterances, _ = pipeline.process_chunk(
            session_id="session-test",
            chunk=b"final-only",
        )

        assert len(utterances) == 1
        assert utterances[0].segment_id == "seg-live-7"
        assert utterances[0].seq_num == 7

    def test_이미_소비한_preview는_grace_matching으로_재사용하지_않는다(self, isolated_database):
        self._save_session(isolated_database)
        pipeline = AudioPipelineService(
            segmenter=_OldSegmenter(),
            speech_to_text_service=_FinalOnlySpeechToTextService(),
            analyzer_service=_NoOpAnalyzer(),
            utterance_repository=SQLiteUtteranceRepository(isolated_database),
            event_service=MeetingEventService(SQLiteMeetingEventRepository(isolated_database)),
            transcription_guard=TranscriptionGuard(TranscriptionGuardConfig()),
            transaction_manager=isolated_database,
            segment_grace_match_max_gap_ms=1_500,
        )
        pipeline._alignment_manager.prime_recent_preview_for_test(
            seq_num=7,
            segment_id="seg-live-7",
            seen_at_ms=pipeline._now_ms(),
            consumed_segment_id="seg-live-7",
        )

        utterances, _ = pipeline.process_chunk(
            session_id="session-test",
            chunk=b"final-only",
        )

        assert len(utterances) == 1
        assert utterances[0].segment_id.startswith("seg-1000-2000")

    def test_segment_정합성_누적_로그를_남긴다(self, isolated_database, caplog):
        self._save_session(isolated_database)
        pipeline = AudioPipelineService(
            segmenter=SpeechSegmenter(),
            speech_to_text_service=_StreamingSpeechToTextServiceWithFinal(),
            analyzer_service=_NoOpAnalyzer(),
            utterance_repository=SQLiteUtteranceRepository(isolated_database),
            event_service=MeetingEventService(SQLiteMeetingEventRepository(isolated_database)),
            transcription_guard=TranscriptionGuard(TranscriptionGuardConfig()),
            transaction_manager=isolated_database,
        )

        with caplog.at_level(logging.INFO):
            pipeline.process_chunk(
                session_id="session-test",
                chunk=b"partial-and-final",
            )

        assert "segment 정합성 누적" in caplog.text


