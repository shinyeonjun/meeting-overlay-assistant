"""오디오 영역의 test audio stream schema 동작을 검증한다."""
from server.app.api.http.serializers.audio import (
    build_stream_error_payload,
    build_stream_payload,
)
from server.app.domain.models.meeting_event import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.domain.shared.enums import EventPriority, EventState, EventType
from server.app.services.audio.pipeline.models.live_stream_utterance import LiveStreamUtterance


class TestAudioStreamSchema:
    """AudioStreamSchema 동작을 검증한다."""
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
        assert payload["utterances"][0]["kind"] == "archive_final"
        assert payload["utterances"][0]["revision"] is None
        assert payload["utterances"][0]["input_source"] == "mic"
        assert payload["utterances"][0]["stability"] == "final"
        assert payload["events"][0]["speaker_label"] == "SPEAKER_00"
        assert payload["events"][0]["type"] == "question"
        assert payload["events"][0]["evidence_text"] == "질문 하나 있습니다."
        assert payload["events"][0]["source_utterance_id"] == utterance.id

    def test_stream_error_payload가_에러_필드를_포함한다(self):
        payload = build_stream_error_payload("session-1", "boom")

        assert payload["session_id"] == "session-1"
        assert payload["input_source"] is None
        assert payload["utterances"] == []
        assert payload["events"] == []
        assert payload["error"] == "boom"

    def test_preview_utterance도_공용_스키마로_직렬화된다(self):
        preview = LiveStreamUtterance.create(
            seq_num=7,
            segment_id="seg-live-test",
            start_ms=1000,
            end_ms=1000,
            text="안녕하",
            confidence=0.71,
            kind="preview",
            revision=3,
            stability="low",
        )

        payload = build_stream_payload("session-1", [preview], [], input_source="system_audio")

        assert payload["utterances"][0]["is_partial"] is True
        assert payload["utterances"][0]["kind"] == "preview"
        assert payload["utterances"][0]["revision"] == 3
        assert payload["utterances"][0]["input_source"] == "system_audio"
        assert payload["utterances"][0]["stability"] == "low"
        assert payload["events"] == []

    def test_live_final_utterance도_공용_스키마로_직렬화된다(self):
        live_final = LiveStreamUtterance.create(
            seq_num=8,
            segment_id="seg-live-fast",
            start_ms=1200,
            end_ms=1200,
            text="안녕하세요",
            confidence=0.79,
            kind="live_final",
            revision=2,
            stability="medium",
        )

        payload = build_stream_payload("session-1", [live_final], [], input_source="system_audio")

        assert payload["utterances"][0]["is_partial"] is True
        assert payload["utterances"][0]["kind"] == "live_final"
        assert payload["utterances"][0]["stability"] == "medium"

    def test_late_archive_final_utterance는_partial이_아니다(self):
        late_archive_final = LiveStreamUtterance.create(
            seq_num=9,
            segment_id="seg-live-late",
            start_ms=1500,
            end_ms=1800,
            text="늦게 도착한 확정 자막",
            confidence=0.83,
            kind="late_archive_final",
            revision=None,
            stability="final",
        )

        payload = build_stream_payload("session-1", [late_archive_final], [], input_source="system_audio")

        assert payload["utterances"][0]["is_partial"] is False
        assert payload["utterances"][0]["kind"] == "late_archive_final"
        assert payload["utterances"][0]["stability"] == "final"

