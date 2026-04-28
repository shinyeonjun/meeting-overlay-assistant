"""회의록 AI 분석 서비스 테스트."""

from __future__ import annotations

import json
from dataclasses import replace

from server.app.domain.events.meeting_event import MeetingEvent
from server.app.domain.shared.enums import EventState, EventType
from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)
from server.app.services.reports.composition.report_document import (
    ReportDocumentV1,
    ReportListItem,
)
from server.app.services.reports.composition.report_document_mapper import (
    ReportSessionContext,
)
from server.app.services.reports.composition.report_markdown_renderer import (
    render_report_markdown,
)
from server.app.services.reports.generation.helpers.content_preparation import (
    prepare_report_content,
)
from server.app.services.reports.minutes import (
    LLMMeetingMinutesAnalyzer,
    MeetingMinutesAnalyzerConfig,
)


class _FakeCompletionClient:
    def __init__(
        self,
        payload: dict[str, object] | str | list[dict[str, object] | str],
    ) -> None:
        self.payloads = payload if isinstance(payload, list) else [payload]
        self.prompt = ""
        self.prompts: list[str] = []
        self.system_prompt = None
        self.response_schema = None
        self.call_count = 0

    def complete(
        self,
        prompt: str,
        *,
        system_prompt=None,
        response_schema=None,
        keep_alive=None,
    ) -> str:
        del keep_alive
        self.prompt = prompt
        self.prompts.append(prompt)
        self.system_prompt = system_prompt
        self.response_schema = response_schema
        payload = self.payloads[min(self.call_count, len(self.payloads) - 1)]
        self.call_count += 1
        if isinstance(payload, str):
            return payload
        return json.dumps(payload, ensure_ascii=False)


class _EmptyEventRepository:
    def list_by_session(self, session_id: str, insight_scope: str | None = None) -> list:
        del session_id, insight_scope
        return []


class _StubMeetingMinutesAnalyzer:
    def __init__(self) -> None:
        self.received_transcript: list[SpeakerTranscriptSegment] = []

    def analyze(
        self,
        *,
        session_id: str,
        session_context,
        speaker_transcript: list[SpeakerTranscriptSegment],
        events: list,
        fallback_document: ReportDocumentV1,
    ) -> ReportDocumentV1:
        del session_id, session_context, events
        self.received_transcript = speaker_transcript
        return replace(
            fallback_document,
            discussion=(ReportListItem("AI가 전사 전체를 보고 논의 내용을 정리했다."),),
        )


def test_llm_meeting_minutes_analyzer가_stt를_보내고_정본_섹션을_반환한다() -> None:
    payload = {
        "agenda": "CAPS 1차 배포 범위와 QA 후속 작업 점검",
        "overview": [
            "1차 배포 범위와 QA 후속 작업을 논의했다.",
        ],
        "sections": [
            {
                "title": "배포 범위 확정",
                "time_range": "00:02-00:05",
                "background": [
                    "1차 배포 범위를 확정하기 위해 MVP 포함 기능을 점검했다.",
                ],
                "opinions": [
                    "로그인과 회의록 조회를 우선 배포하자는 의견이 제시되었다.",
                ],
                "review": [
                    "검색 화면 회귀 테스트 일정이 부족할 가능성을 함께 검토했다.",
                ],
                "direction": [
                    "1차 배포는 로그인과 회의록 조회 중심으로 진행한다.",
                ],
            }
        ],
        "special_notes": [
            {
                "text": "검색 화면 회귀 테스트 시간이 부족할 수 있다.",
                "evidence": "검색 화면은 시간이 부족할 수 있다.",
                "time_range": "00:05-00:08",
            }
        ],
        "decisions": [
            {
                "text": "1차 배포는 로그인과 회의록 조회로 제한한다.",
                "evidence": "이번 주에는 로그인과 회의록 조회만 배포합시다.",
                "time_range": "00:02-00:05",
            }
        ],
        "follow_up": [
            {
                "task": "민수가 QA 체크리스트를 정리한다.",
                "owner": "민수",
                "due_date": "미기록",
                "status": "대기",
                "note": "회의 중 담당자로 언급됨",
                "time_range": "00:08-00:10",
            }
        ],
    }
    completion_client = _FakeCompletionClient(payload)
    analyzer = LLMMeetingMinutesAnalyzer(
        completion_client,
        config=MeetingMinutesAnalyzerConfig(model="test-model"),
    )
    fallback_document = ReportDocumentV1(
        title="CAPS 릴리즈 점검",
        agenda=(ReportListItem("fallback agenda"),),
    )
    speaker_transcript = [
        SpeakerTranscriptSegment(
            speaker_label="SPEAKER_00",
            start_ms=2000,
            end_ms=5000,
            text="이번 주에는 로그인과 회의록 조회만 배포합시다.",
            confidence=0.94,
        ),
        SpeakerTranscriptSegment(
            speaker_label="SPEAKER_01",
            start_ms=8000,
            end_ms=10000,
            text="민수가 QA 체크리스트를 정리하겠습니다.",
            confidence=0.93,
        ),
    ]

    document = analyzer.analyze(
        session_id="session-doc",
        session_context=ReportSessionContext(session_id="session-doc"),
        speaker_transcript=speaker_transcript,
        events=[],
        fallback_document=fallback_document,
    )
    markdown = render_report_markdown(session_id="session-doc", document=document)

    assert document is not None
    assert "이번 주에는 로그인과 회의록 조회만 배포합시다." in completion_client.prompt
    assert completion_client.response_schema is not None
    assert completion_client.system_prompt is not None
    assert "STT 원문을 그대로 옮기지 말고" in completion_client.system_prompt
    assert "회의록은 전사 요약본이 아니라 안건 중심 문서로 작성한다." in completion_client.system_prompt
    assert "여러 발화를 하나의 논의 주제로 묶어 정리한다." in completion_client.system_prompt
    assert "사용자에게 공유되는 회의록에 근거 구간, 발화자, 원문 인용을 노출하지 않는다." in completion_client.system_prompt
    assert "SPEAKER_00, SPEAKER_01 같은 시스템 화자 라벨은 최종 문장에 절대 쓰지 않는다." in completion_client.system_prompt
    assert '"생각합니다", "나왔습니다", "단어 사용"' in completion_client.system_prompt
    assert "간결한 공식 문서체로 쓴다." in completion_client.system_prompt
    assert "agenda: 회의개요의 안건 칸에 들어갈 회의 전체 주제 1개만 작성한다." in completion_client.system_prompt
    assert "sections.title: 회의내용 안에서 사용할 소주제명만 짧게 적는다." in completion_client.system_prompt
    assert "sections.background: 해당 소주제가 왜 논의되었는지 배경을 적는다." in completion_client.system_prompt
    assert "sections.opinions: 참석자들이 낸 주요 의견" in completion_client.system_prompt
    assert "sections.review: 비교, 검토, 우려, 확인 필요 내용을 정리한다." in completion_client.system_prompt
    assert "sections.direction: 논의 결과 정리된 방향을 적는다." in completion_client.system_prompt
    assert "decisions: 회의에서 합의되었거나 확정된 결정사항만 적는다." in completion_client.system_prompt
    assert "agenda는 회의 전체를 대표하는 주제 한 줄이어야 하며" in completion_client.system_prompt
    assert "agenda에는 여러 논의 항목을 나열하지 않는다." in completion_client.system_prompt
    assert "sections.title에는 세부 내용을 반복해서 쓰지 말고" in completion_client.system_prompt
    assert "질문 문장, 감탄, 농담, 맞장구를 그대로 넣지 말고" in completion_client.system_prompt
    assert "비주얼 요소 개선 필요성이 제기됨" in completion_client.system_prompt
    assert "특정 단어가 쓰였다는 메타 설명은 쓰지 않는다." in completion_client.system_prompt
    assert "decisions에는 단순 의견, 아이디어, 질문, 할 일을 넣지 않는다." in completion_client.system_prompt
    assert "합의 여부가 불명확한 표현은 decisions에 넣지 말고 sections에 넣는다." in completion_client.system_prompt
    assert "special_notes는 반복 요약이나 중요 주제 목록이 아니다." in completion_client.system_prompt
    assert "같은 내용을 sections, decisions, special_notes, follow_up에 반복해서 넣지 않는다." in completion_client.system_prompt
    assert document.summary[0] == "1차 배포 범위와 QA 후속 작업을 논의했다."
    assert document.sections[0].title == "배포 범위 확정"
    assert document.sections[0].background[0].text == "1차 배포 범위를 확정하기 위해 MVP 포함 기능을 점검했다."
    assert document.sections[0].opinions[0].text == "로그인과 회의록 조회를 우선 배포하자는 의견이 제시되었다."
    assert document.sections[0].review[0].text == "검색 화면 회귀 테스트 일정이 부족할 가능성을 함께 검토했다."
    assert document.sections[0].direction[0].text == "1차 배포는 로그인과 회의록 조회 중심으로 진행한다."
    assert document.agenda[0].text == "CAPS 1차 배포 범위와 QA 후속 작업 점검"
    assert document.discussion[-1].text == "1차 배포는 로그인과 회의록 조회 중심으로 진행한다."
    assert document.decisions[0].text == "1차 배포는 로그인과 회의록 조회로 제한한다."
    assert document.risks[0].text == "검색 화면 회귀 테스트 시간이 부족할 수 있다."
    assert document.action_items[0].task == "민수가 QA 체크리스트를 정리한다."
    assert document.action_items[0].owner == "민수"
    assert document.action_items[0].due_date == ""
    assert document.action_items[0].status == ""
    assert "- 안건: CAPS 1차 배포 범위와 QA 후속 작업 점검" in markdown
    assert "## 회의내용" in markdown
    assert "## 결정사항" in markdown
    assert "1. 배포 범위 확정" in markdown
    assert "  - 논의 배경" in markdown
    assert "    - 1차 배포 범위를 확정하기 위해 MVP 포함 기능을 점검했다." in markdown
    assert "  - 정리된 방향" in markdown
    assert "    - 1차 배포는 로그인과 회의록 조회 중심으로 진행한다." in markdown
    assert "1. 1차 배포는 로그인과 회의록 조회로 제한한다." in markdown


def test_llm_meeting_minutes_analyzer가_실패하면_fallback을_유지한다() -> None:
    analyzer = LLMMeetingMinutesAnalyzer(
        _FakeCompletionClient("not-json"),
        config=MeetingMinutesAnalyzerConfig(model="test-model"),
    )

    document = analyzer.analyze(
        session_id="session-doc",
        session_context=None,
        speaker_transcript=[
            SpeakerTranscriptSegment(
                speaker_label="SPEAKER_00",
                start_ms=0,
                end_ms=1000,
                text="회의 내용",
                confidence=0.9,
            )
        ],
        events=[],
        fallback_document=ReportDocumentV1(title="fallback"),
    )

    assert document is None


def test_prepare_report_content는_ai_분석_실패를_generation_warning으로_남긴다() -> None:
    analyzer = LLMMeetingMinutesAnalyzer(
        _FakeCompletionClient("not-json"),
        config=MeetingMinutesAnalyzerConfig(model="test-model"),
    )
    speaker_transcript = [
        SpeakerTranscriptSegment(
            speaker_label="SPEAKER_00",
            start_ms=0,
            end_ms=1200,
            text="회의록 생성을 위한 논의입니다.",
            confidence=0.95,
        )
    ]

    prepared = prepare_report_content(
        session_id="session-doc",
        audio_path=None,
        live_events=[],
        canonical_speaker_transcript=speaker_transcript,
        event_repository=_EmptyEventRepository(),
        audio_postprocessing_service=None,
        speaker_event_projection_service=None,
        meeting_minutes_analyzer=analyzer,
    )

    assert prepared.generation_warning is not None
    assert "기본 회의록" in prepared.generation_warning
    assert prepared.analysis_snapshot is not None
    assert prepared.analysis_snapshot["generation_warning"] == prepared.generation_warning


def test_llm_meeting_minutes_analyzer는_schema_없이도_json_응답을_파싱한다() -> None:
    completion_client = _FakeCompletionClient(
        """```json
{
  "agenda": "회의록 구조 개편 방향 정리",
  "overview": ["회의록 구조를 계층형으로 정리했다."],
  "sections": [
    {
      "title": "회의록 구조 개편",
      "time_range": "00:01-00:04",
      "background": ["회의록 구조를 더 읽기 쉽게 만들 필요가 있었다."],
      "opinions": ["안건과 논의 내용을 주제 아래로 묶자는 의견이 나왔다."],
      "review": [],
      "direction": ["안건과 논의 내용을 주제 아래로 묶는 방식으로 정리한다."]
    }
  ],
  "special_notes": [],
  "decisions": [],
  "follow_up": []
}
```"""
    )
    analyzer = LLMMeetingMinutesAnalyzer(
        completion_client,
        config=MeetingMinutesAnalyzerConfig(
            model="test-model",
            use_response_schema=False,
        ),
    )

    document = analyzer.analyze(
        session_id="session-doc",
        session_context=None,
        speaker_transcript=[
            SpeakerTranscriptSegment(
                speaker_label="SPEAKER_00",
                start_ms=1000,
                end_ms=4000,
                text="안건 밑에 논의 내용을 붙입시다.",
                confidence=0.9,
            )
        ],
        events=[],
        fallback_document=ReportDocumentV1(title="fallback"),
    )

    assert completion_client.response_schema is None
    assert document is not None
    assert document.summary[0] == "회의록 구조를 계층형으로 정리했다."
    assert document.sections[0].title == "회의록 구조 개편"
    assert document.sections[0].direction[0].text == "안건과 논의 내용을 주제 아래로 묶는 방식으로 정리한다."
    assert document.agenda[0].text == "회의록 구조 개편 방향 정리"
    assert document.discussion[-1].text == "안건과 논의 내용을 주제 아래로 묶는 방식으로 정리한다."


def test_llm_meeting_minutes_analyzer는_긴_전사를_분할_분석해서_병합한다() -> None:
    completion_client = _FakeCompletionClient(
        [
            {
                "agenda": "된장찌개 상품 개선 전략 논의",
                "overview": ["비주얼 개선 방향을 논의했다."],
                "sections": [
                    {
                        "title": "비주얼 개선",
                        "time_range": None,
                        "background": ["SNS 노출을 위해 사진에 잘 보이는 구성이 필요했다."],
                        "opinions": ["전골냄비와 붉은색 재료를 활용하자는 의견이 제시되었다."],
                        "review": [],
                        "direction": ["메인 요리처럼 보이도록 플레이팅을 개선한다."],
                    }
                ],
                "special_notes": [],
                "decisions": [],
                "follow_up": [],
            },
            {
                "agenda": "된장찌개 상품 개선 전략 논의",
                "overview": ["재료와 육수 강화 방향을 검토했다."],
                "sections": [
                    {
                        "title": "재료 및 육수 강화",
                        "time_range": None,
                        "background": ["맛의 깊이를 높일 핵심 요소를 정리할 필요가 있었다."],
                        "opinions": ["고기 육수와 해산물 재료를 활용하자는 의견이 제시되었다."],
                        "review": ["다양한 재료를 넣되 된장찌개 본연의 맛을 유지해야 한다."],
                        "direction": ["육수와 주요 재료를 강화하는 방향으로 검토한다."],
                    }
                ],
                "special_notes": [{"text": "본연의 맛을 잃지 않도록 주의가 필요하다."}],
                "decisions": [{"text": "육수 강화 방안을 우선 검토한다."}],
                "follow_up": [],
            },
        ]
    )
    analyzer = LLMMeetingMinutesAnalyzer(
        completion_client,
        config=MeetingMinutesAnalyzerConfig(
            model="test-model",
            map_reduce_segment_threshold=2,
            max_segments_per_chunk=2,
        ),
    )
    speaker_transcript = [
        SpeakerTranscriptSegment(
            speaker_label="SPEAKER_00",
            start_ms=index * 1000,
            end_ms=(index + 1) * 1000,
            text=f"회의 발화 {index}",
            confidence=0.9,
        )
        for index in range(5)
    ]

    document = analyzer.analyze(
        session_id="session-doc",
        session_context=None,
        speaker_transcript=speaker_transcript,
        events=[],
        fallback_document=ReportDocumentV1(title="fallback"),
    )

    assert completion_client.call_count == 3
    assert all('"analysis_scope":"chunk ' in prompt for prompt in completion_client.prompts)
    assert document is not None
    assert document.agenda[0].text == "된장찌개 상품 개선 전략 논의"
    assert [section.title for section in document.sections] == [
        "비주얼 개선",
        "재료 및 육수 강화",
    ]
    assert document.decisions[0].text == "육수 강화 방안을 우선 검토한다."
    assert document.risks[0].text == "본연의 맛을 잃지 않도록 주의가 필요하다."


def test_llm_meeting_minutes_analyzer는_논의가_없는_섹션도_안건으로_유지한다() -> None:
    completion_client = _FakeCompletionClient(
        {
            "agenda": "회의록 비주얼 개선 방향 점검",
            "overview": ["회의 주제를 확인했다."],
            "sections": [
                {
                    "title": "비주얼",
                    "time_range": None,
                    "background": [],
                    "opinions": [],
                    "review": [],
                    "direction": [],
                }
            ],
            "special_notes": [],
            "decisions": [],
            "follow_up": [],
        }
    )
    analyzer = LLMMeetingMinutesAnalyzer(
        completion_client,
        config=MeetingMinutesAnalyzerConfig(model="test-model"),
    )

    document = analyzer.analyze(
        session_id="session-doc",
        session_context=None,
        speaker_transcript=[
            SpeakerTranscriptSegment(
                speaker_label="SPEAKER_00",
                start_ms=0,
                end_ms=1000,
                text="비주얼을 더 신경 써야 합니다.",
                confidence=0.9,
            )
        ],
        events=[],
        fallback_document=ReportDocumentV1(title="fallback"),
    )

    assert document is not None
    assert document.summary == ("회의 주제를 확인했다.",)
    assert document.sections[0].title == "비주얼"
    assert document.sections[0].discussion == ()
    assert document.sections[0].background == ()
    assert document.sections[0].direction == ()
    assert document.agenda[0].text == "회의록 비주얼 개선 방향 점검"
    assert document.discussion == ()


def test_prepare_report_content가_ai_회의록_분석_결과를_렌더링에_사용한다() -> None:
    meeting_minutes_analyzer = _StubMeetingMinutesAnalyzer()
    speaker_transcript = [
        SpeakerTranscriptSegment(
            speaker_label="SPEAKER_00",
            start_ms=0,
            end_ms=1200,
            text="회의록 생성은 전사 전체를 기준으로 분석합시다.",
            confidence=0.95,
        )
    ]
    events = [
        MeetingEvent.create(
            session_id="session-doc",
            event_type=EventType.DECISION,
            title="기존 이벤트 fallback",
            state=EventState.CONFIRMED,
            source_utterance_id="utt-1",
        )
    ]

    prepared = prepare_report_content(
        session_id="session-doc",
        audio_path=None,
        live_events=events,
        canonical_speaker_transcript=speaker_transcript,
        event_repository=_EmptyEventRepository(),
        audio_postprocessing_service=None,
        speaker_event_projection_service=None,
        meeting_minutes_analyzer=meeting_minutes_analyzer,
    )

    assert meeting_minutes_analyzer.received_transcript == speaker_transcript
    assert prepared.report_document.discussion[0].text == "AI가 전사 전체를 보고 논의 내용을 정리했다."
    assert "AI가 전사 전체를 보고 논의 내용을 정리했다." in prepared.markdown_content
