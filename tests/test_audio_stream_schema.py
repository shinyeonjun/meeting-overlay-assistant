"""오디오 스트림 스키마 직렬화 테스트."""

from backend.app.api.http.serializers.audio import (
    build_stream_error_payload,
    build_stream_payload,
)
from backend.app.domain.models.meeting_event import MeetingEvent
from backend.app.domain.models.utterance import Utterance
from backend.app.domain.shared.enums import EventPriority, EventState, EventType
from backend.app.services.audio.pipeline.live_stream_utterance import LiveStreamUtterance


class TestAudioStreamSchema:
    def test_stream_payload가_공용_스키마로_직렬화된다(self):
        utterance = Utterance.create(
            session_id="session-1",
            seq_num=1,
            start_ms=100,
            end_ms=900,
            text="질문 하나 있습니다.",
            confidence=0.91,
        )
        event = MeetingEvent.create(
            session_id="session-1",
            event_type=EventType.QUESTION,
            title="질문 하나 있습니다.",
            evidence_text="질문 하나 있습니다.",
            state=EventState.CONFIRMED,
            priority=EventPriority.QUESTION,
            source_utterance_id=utterance.id,
            speaker_label="SPEAKER_00",
        )

        payload = build_stream_payload("session-1", [utterance], [event], input_source="mic")

        assert payload["session_id"] == "session-1"
        assert payload["input_source"] == "mic"
        assert payload["utterances"][0]["start_ms"] == 100
        assert payload["utterances"][0]["end_ms"] == 900
        assert payload["utterances"][0]["is_partial"] is False
        assert payload["utterances"][0]["kind"] == "final"
        assert payload["utterances"][0]["revision"] is None
        assert payload["utterances"][0]["input_source"] == "mic"
        assert payload["events"][0]["speaker_label"] == "SPEAKER_00"
        assert payload["events"][0]["type"] == "question"
        assert payload["events"][0]["evidence_text"] == "질문 하나 있습니다."
        assert payload["events"][0]["input_source"] == "mic"

    def test_stream_error_payload가_에러_필드를_포함한다(self):
        payload = build_stream_error_payload("session-1", "boom")

        assert payload["session_id"] == "session-1"
        assert payload["input_source"] is None
        assert payload["utterances"] == []
        assert payload["events"] == []
        assert payload["error"] == "boom"

    def test_partial_utterance도_공용_스키마로_직렬화된다(self):
        partial = LiveStreamUtterance.create(
            seq_num=7,
            segment_id="seg-live-test",
            start_ms=1000,
            end_ms=1000,
            text="안녕하",
            confidence=0.71,
            kind="partial",
            revision=3,
        )

        payload = build_stream_payload("session-1", [partial], [], input_source="system_audio")

        assert payload["utterances"][0]["is_partial"] is True
        assert payload["utterances"][0]["kind"] == "partial"
        assert payload["utterances"][0]["revision"] == 3
        assert payload["utterances"][0]["input_source"] == "system_audio"
        assert payload["events"] == []

