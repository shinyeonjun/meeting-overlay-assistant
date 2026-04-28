"""회의록 정본 문서 mapper 테스트."""

import wave

from server.app.domain.events.meeting_event import MeetingEvent
from server.app.domain.shared.enums import EventState, EventType
from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)
from server.app.services.reports.composition.html_report_template import (
    render_report_html,
)
from server.app.services.reports.composition.report_document_mapper import (
    ReportSessionContext,
    build_report_document_v1,
)
from server.app.services.reports.composition.report_markdown_renderer import (
    render_report_markdown,
)
from server.app.services.reports.composition.speaker_event_projection_service import (
    SpeakerAttributedEvent,
)
from server.app.services.reports.generation.helpers.recording_metadata import (
    read_recording_file_metadata,
)


def test_report_document_v1을_실제_이벤트와_전사에서_생성한다() -> None:
    events = [
        MeetingEvent.create(
            session_id="session-doc",
            event_type=EventType.QUESTION,
            title="배포 전 QA 범위를 어디까지 볼까요?",
            state=EventState.OPEN,
            source_utterance_id="utt-1",
            evidence_text="배포 전 QA 범위를 어디까지 볼까요?",
            speaker_label="SPEAKER_00",
        ),
        MeetingEvent.create(
            session_id="session-doc",
            event_type=EventType.DECISION,
            title="1차 배포 범위는 로그인과 회의록 조회로 제한한다.",
            state=EventState.CONFIRMED,
            source_utterance_id="utt-2",
            evidence_text="이번 주에는 로그인과 회의록 조회만 배포합시다.",
            speaker_label="SPEAKER_01",
        ),
        MeetingEvent.create(
            session_id="session-doc",
            event_type=EventType.ACTION_ITEM,
            title="민수가 QA 체크리스트를 정리한다.",
            state=EventState.OPEN,
            source_utterance_id="utt-3",
            evidence_text="민수가 QA 체크리스트를 정리하겠습니다.",
            speaker_label="SPEAKER_02",
        ),
        MeetingEvent.create(
            session_id="session-doc",
            event_type=EventType.RISK,
            title="검색 화면 회귀 테스트 시간이 부족할 수 있다.",
            state=EventState.OPEN,
            source_utterance_id="utt-4",
            evidence_text="검색 화면은 회귀 테스트 시간이 부족할 수 있습니다.",
            speaker_label="SPEAKER_01",
        ),
    ]
    speaker_transcript = [
        SpeakerTranscriptSegment(
            speaker_label="SPEAKER_00",
            start_ms=0,
            end_ms=2400,
            text="배포 전 QA 범위를 어디까지 볼까요?",
            confidence=0.95,
        ),
        SpeakerTranscriptSegment(
            speaker_label="SPEAKER_01",
            start_ms=2500,
            end_ms=5800,
            text="이번 주에는 로그인과 회의록 조회만 배포합시다.",
            confidence=0.94,
        ),
        SpeakerTranscriptSegment(
            speaker_label="SPEAKER_02",
            start_ms=5900,
            end_ms=8300,
            text="민수가 QA 체크리스트를 정리하겠습니다.",
            confidence=0.93,
        ),
    ]
    speaker_events = [
        SpeakerAttributedEvent(speaker_label="SPEAKER_01", event=events[1])
    ]

    document = build_report_document_v1(
        session_id="session-doc",
        events=events,
        speaker_transcript=speaker_transcript,
        speaker_events=speaker_events,
        insight_source="high_precision_audio",
        session_context=ReportSessionContext(
            session_id="session-doc",
            title="CAPS 릴리즈 점검",
            started_at="2026-04-25T01:00:00+00:00",
            ended_at="2026-04-25T01:45:00+00:00",
            participants=("민수", "지현"),
            organizer="제품팀",
            primary_input_source="system_audio",
            actual_active_sources=("mic", "system_audio"),
        ),
    )
    markdown = render_report_markdown(session_id="session-doc", document=document)
    html = render_report_html(document)

    metadata = {item.label: item.value for item in document.metadata}
    assert document.title == "CAPS 릴리즈 점검"
    assert metadata["회의제목"] == "CAPS 릴리즈 점검"
    assert metadata["일시"] == "2026-04-25 10:00 - 10:45"
    assert metadata["장소"] == ""
    assert metadata["작성자"] == "제품팀"
    assert metadata["작성일"] == "2026-04-25"
    assert metadata["참석자"] == "민수, 지현"
    assert metadata["회의 주최자"] == "제품팀"
    assert document.agenda[0].text == "CAPS 릴리즈 점검"
    assert document.decisions[0].text == "1차 배포 범위는 로그인과 회의록 조회로 제한한다."
    assert document.action_items[0].task == "민수가 QA 체크리스트를 정리한다."
    assert document.action_items[0].owner == ""
    assert document.action_items[0].status == ""
    assert document.action_items[0].time_range == "00:05-00:08"
    assert document.decisions[0].time_range == "00:02-00:05"
    assert document.transcript_excerpt == (
        "[SPEAKER_00] 00:00-00:02 배포 전 QA 범위를 어디까지 볼까요?",
        "[SPEAKER_01] 00:02-00:05 이번 주에는 로그인과 회의록 조회만 배포합시다.",
        "[SPEAKER_02] 00:05-00:08 민수가 QA 체크리스트를 정리하겠습니다.",
    )
    assert markdown.startswith("# 회의록")
    assert "## 회의 개요" in markdown
    assert "- 안건: CAPS 릴리즈 점검" in markdown
    assert "## 회의내용" in markdown
    assert "## 결정사항" in markdown
    assert "## 특이사항" in markdown
    assert "## 향후일정" in markdown
    assert "작성자: CAPS" not in markdown
    assert "## 발화자 기반 인사이트" not in markdown
    assert "## 참고 전사" not in markdown
    assert "1. 1차 배포 범위는 로그인과 회의록 조회로 제한한다." in markdown
    assert "근거 구간" not in markdown
    assert "회의록" in html
    assert "회의개요" in html
    assert "일시" in html
    assert "장소" in html
    assert "작성자" in html
    assert "작성일" in html
    assert "안건" in html
    assert "회의내용" in html
    assert "결정사항" in html
    assert "특이사항" in html
    assert "향후일정" in html
    assert "작성자: CAPS" not in html
    assert "근거 구간" not in html
    assert "발화자 기반 인사이트" not in html
    assert "참고 전사" not in html
    assert "민수가 QA 체크리스트를 정리한다." in html


def test_question_only_event는_논의내용_fallback에_들어가지_않는다() -> None:
    question = MeetingEvent.create(
        session_id="session-doc",
        event_type=EventType.QUESTION,
        title="배포 전 QA 범위를 어디까지 볼까요?",
        state=EventState.OPEN,
        source_utterance_id="utt-1",
        evidence_text="배포 전 QA 범위를 어디까지 볼까요?",
        speaker_label="SPEAKER_00",
    )

    document = build_report_document_v1(
        session_id="session-doc",
        events=[question],
        speaker_transcript=[
            SpeakerTranscriptSegment(
                speaker_label="SPEAKER_00",
                start_ms=0,
                end_ms=2400,
                text="배포 전 QA 범위를 어디까지 볼까요?",
                confidence=0.95,
            )
        ],
        speaker_events=[],
        insight_source="high_precision_audio",
    )
    markdown = render_report_markdown(session_id="session-doc", document=document)
    html = render_report_html(document)

    assert "- 안건: 배포 전 QA 범위를 어디까지 볼까요?" in markdown
    assert "## 회의내용\n- 없음" in markdown
    assert "기록된 내용이 없습니다." in html


def test_report_document_v1이_비액션_후속조치와_긴_근거를_정리한다() -> None:
    non_action_text = "그냥 농담으로 하신 말씀인데 제가 오버한 거죠?"
    long_action_title = "민수가 QA 체크리스트를 정리한다. " * 16
    long_evidence = "민수가 QA 체크리스트를 정리해서 공유하겠습니다. " * 8
    events = [
        MeetingEvent.create(
            session_id="session-doc",
            event_type=EventType.ACTION_ITEM,
            title=non_action_text,
            state=EventState.OPEN,
            source_utterance_id="utt-1",
            evidence_text=non_action_text,
            speaker_label="SPEAKER_00",
        ),
        MeetingEvent.create(
            session_id="session-doc",
            event_type=EventType.ACTION_ITEM,
            title=long_action_title,
            state=EventState.OPEN,
            source_utterance_id="utt-2",
            evidence_text=long_evidence,
            speaker_label="SPEAKER_01",
        ),
    ]
    speaker_transcript = [
        SpeakerTranscriptSegment(
            speaker_label="SPEAKER_01",
            start_ms=0,
            end_ms=2400,
            text=long_evidence,
            confidence=0.95,
        ),
    ]

    document = build_report_document_v1(
        session_id="session-doc",
        events=events,
        speaker_transcript=speaker_transcript,
        speaker_events=[
            SpeakerAttributedEvent(speaker_label="SPEAKER_00", event=events[0]),
            SpeakerAttributedEvent(speaker_label="SPEAKER_01", event=events[1]),
        ],
        insight_source="high_precision_audio",
    )

    assert len(document.action_items) == 1
    assert document.action_items[0].task.endswith("…")
    assert len(document.action_items[0].task) <= 140
    assert document.action_items[0].note.endswith("…")
    assert len(document.action_items[0].note) <= 160
    assert non_action_text not in " ".join(item.text for item in document.agenda)
    assert non_action_text not in " ".join(document.speaker_insights)
    assert document.speaker_insights[0].endswith("…")


def test_report_document_v1은_녹음_길이로_회의_종료_시각을_보정한다() -> None:
    speaker_transcript = [
        SpeakerTranscriptSegment(
            speaker_label="SPEAKER_00",
            start_ms=0,
            end_ms=420_000,
            text="녹음 길이 기준으로 회의 시간이 계산되어야 합니다.",
            confidence=0.95,
        ),
    ]

    document = build_report_document_v1(
        session_id="session-doc",
        events=[],
        speaker_transcript=speaker_transcript,
        speaker_events=[],
        insight_source="high_precision_audio",
        session_context=ReportSessionContext(
            session_id="session-doc",
            title="녹음 메타데이터 회의",
            started_at="2026-04-04T02:15:00+00:00",
            ended_at="2026-04-04T02:15:01+00:00",
        ),
    )

    metadata = {item.label: item.value for item in document.metadata}
    assert metadata["일시"] == "2026-04-04 11:15 - 11:22"


def test_report_document_v1은_짧은_녹음의_초단위_시간을_표시한다() -> None:
    speaker_transcript = [
        SpeakerTranscriptSegment(
            speaker_label="SPEAKER_00",
            start_ms=0,
            end_ms=15_000,
            text="짧은 회의는 초 단위가 보여야 합니다.",
            confidence=0.95,
        ),
    ]

    document = build_report_document_v1(
        session_id="session-doc",
        events=[],
        speaker_transcript=speaker_transcript,
        speaker_events=[],
        insight_source="high_precision_audio",
        session_context=ReportSessionContext(
            session_id="session-doc",
            title="짧은 녹음 회의",
            started_at="2026-04-04T02:15:00+00:00",
        ),
    )

    metadata = {item.label: item.value for item in document.metadata}
    assert metadata["일시"] == "2026-04-04 11:15:00 - 11:15:15"


def test_read_recording_file_metadata는_wav_길이를_읽는다(tmp_path) -> None:
    wav_path = tmp_path / "sample.wav"
    with wave.open(str(wav_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16_000)
        wav_file.writeframes(b"\0\0" * 16_000)

    metadata = read_recording_file_metadata(wav_path)

    assert metadata.file_modified_at is not None
    assert metadata.duration_ms == 1000
