"""회의록 정본 문서 mapper 테스트."""

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
            primary_input_source="system_audio",
            actual_active_sources=("mic", "system_audio"),
        ),
    )
    markdown = render_report_markdown(session_id="session-doc", document=document)
    html = render_report_html(document)

    metadata = {item.label: item.value for item in document.metadata}
    assert document.title == "CAPS 릴리즈 점검"
    assert metadata["회의일자"] == "2026-04-25"
    assert metadata["회의시간"] == "10:00 - 10:45"
    assert metadata["회의주제"] == "CAPS 릴리즈 점검"
    assert metadata["참석자"] == "민수, 지현"
    assert metadata["기록 기준"] == "정식 후처리 · 전사 3개 구간 · 추출 이벤트 4건 · 녹음 소스 mic, system_audio"
    assert document.agenda[0].text == "질문: 배포 전 QA 범위를 어디까지 볼까요?"
    assert document.agenda[1].text == "결정: 1차 배포 범위는 로그인과 회의록 조회로 제한한다."
    assert document.decisions[0].text == "1차 배포 범위는 로그인과 회의록 조회로 제한한다."
    assert document.action_items[0].task == "민수가 QA 체크리스트를 정리한다."
    assert document.action_items[0].owner == "SPEAKER_02"
    assert document.action_items[0].status == "대기"
    assert document.action_items[0].time_range == "00:05-00:08"
    assert document.decisions[0].time_range == "00:02-00:05"
    assert document.transcript_excerpt == (
        "[SPEAKER_00] 00:00-00:02 배포 전 QA 범위를 어디까지 볼까요?",
        "[SPEAKER_01] 00:02-00:05 이번 주에는 로그인과 회의록 조회만 배포합시다.",
        "[SPEAKER_02] 00:05-00:08 민수가 QA 체크리스트를 정리하겠습니다.",
    )
    assert markdown.startswith("# CAPS 릴리즈 점검")
    assert "## 회의 개요" in markdown
    assert "## 안건 및 논의" in markdown
    assert "- 회의주제: CAPS 릴리즈 점검" in markdown
    assert "## 결정 사항" in markdown
    assert "## 후속 조치" in markdown
    assert "## 발화자 기반 인사이트" in markdown
    assert "1. 질문: 배포 전 QA 범위를 어디까지 볼까요?" in markdown
    assert "1. 1차 배포 범위는 로그인과 회의록 조회로 제한한다." in markdown
    assert "  - 근거 구간: 00:02-00:05" in markdown
    assert "회의 요약" in html
    assert "안건 및 논의" in html
    assert "근거 구간: 00:02-00:05" in html
    assert "발화자 기반 인사이트" in html
    assert "민수가 QA 체크리스트를 정리한다." in html
