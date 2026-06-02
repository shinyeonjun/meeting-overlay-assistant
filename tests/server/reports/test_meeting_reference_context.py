from __future__ import annotations

import json

from server.app.domain.retrieval import RetrievalSearchResult
from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)
from server.app.services.reports.composition.report_document import ReportDocumentV1
from server.app.services.reports.composition.report_session_context import (
    ReportSessionContext,
)
from server.app.services.reports.generation.helpers.content_preparation import (
    prepare_report_content,
)
from server.app.services.reports.generation.helpers.reference_context import (
    MeetingReferenceContextConfig,
    MeetingReferenceContextService,
)
from server.app.services.reports.minutes import (
    LLMMeetingMinutesAnalyzer,
    MeetingMinutesAnalyzerConfig,
)


class _FakeRetrievalQueryService:
    def __init__(self, results: list[RetrievalSearchResult]) -> None:
        self.results = results
        self.source_types: tuple[str, ...] = ()

    def search(self, **kwargs):
        self.source_types = kwargs["source_types"]
        return self.results


class _FakeCompletionClient:
    def __init__(self) -> None:
        self.prompt = ""
        self.system_prompt = None
        self.response_schema = None

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
        self.system_prompt = system_prompt
        self.response_schema = response_schema
        return json.dumps(
            {
                "agenda": "회의록 RAG 참고 맥락 점검",
                "overview": ["기존 노트 참고 맥락을 회의록 분석 입력에 함께 전달했다."],
                "sections": [
                    {
                        "title": "RAG 참고 맥락",
                        "background": ["회의록 생성에서 기존 노트를 참고한다."],
                        "opinions": [],
                        "review": [],
                        "direction": ["이번 전사에 있는 내용만 회의록에 반영한다."],
                    }
                ],
                "special_notes": [],
                "decisions": [],
                "follow_up": [],
            },
            ensure_ascii=False,
        )


class _EmptyEventRepository:
    def list_by_session(self, session_id: str, insight_scope: str | None = None) -> list:
        del session_id, insight_scope
        return []


class _StubMeetingMinutesAnalyzer:
    def __init__(self) -> None:
        self.received_reference_context: list[dict[str, object]] | None = None

    def analyze(
        self,
        *,
        session_id: str,
        session_context,
        speaker_transcript: list[SpeakerTranscriptSegment],
        events: list,
        fallback_document: ReportDocumentV1,
        reference_context: list[dict[str, object]] | None = None,
    ) -> ReportDocumentV1:
        del session_id, session_context, speaker_transcript, events
        self.received_reference_context = reference_context
        return fallback_document


class _StubMeetingReferenceContextService:
    def retrieve_reference_context(
        self,
        *,
        session_id: str,
        session_context,
        speaker_transcript: list[SpeakerTranscriptSegment],
    ) -> list[dict[str, object]]:
        del session_id, session_context, speaker_transcript
        return [
            {
                "source_type": "note",
                "title": "과거 회의 note transcript",
                "heading": "Transcript",
                "session_id": "previous-session",
                "text": "과거 회의에서 같은 주제를 논의했다.",
            }
        ]


def test_meeting_reference_context_service_searches_notes_and_excludes_current_session() -> None:
    retrieval_service = _FakeRetrievalQueryService(
        [
            RetrievalSearchResult(
                chunk_id="current",
                document_id="doc-current",
                source_type="note",
                source_id="session:session-doc:latest-note",
                document_title="현재 회의 note transcript",
                chunk_text="현재 세션 노트는 제외해야 한다.",
                chunk_heading="Transcript",
                distance=0.1,
                session_id="session-doc",
            ),
            RetrievalSearchResult(
                chunk_id="previous",
                document_id="doc-previous",
                source_type="note",
                source_id="session:previous-session:latest-note",
                document_title="과거 회의 note transcript",
                chunk_text="과거 회의에서 챗봇 RAG를 우선하기로 했다.",
                chunk_heading="Transcript",
                distance=0.2,
                session_id="previous-session",
            ),
        ]
    )
    service = MeetingReferenceContextService(
        retrieval_query_service=retrieval_service,
        config=MeetingReferenceContextConfig(enabled=True, limit=4),
    )

    context = service.retrieve_reference_context(
        session_id="session-doc",
        session_context=ReportSessionContext(
            session_id="session-doc",
            title="챗봇 RAG 점검",
        ),
        speaker_transcript=[
            SpeakerTranscriptSegment(
                speaker_label="SPEAKER_00",
                start_ms=0,
                end_ms=1000,
                text="챗봇 RAG와 회의록 참고 맥락을 점검합니다.",
                confidence=0.95,
            )
        ],
    )

    assert retrieval_service.source_types == ("note",)
    assert len(context) == 1
    assert context[0]["session_id"] == "previous-session"
    assert context[0]["source_type"] == "note"


def test_llm_meeting_minutes_analyzer_adds_reference_context_to_prompt() -> None:
    completion_client = _FakeCompletionClient()
    analyzer = LLMMeetingMinutesAnalyzer(
        completion_client,
        config=MeetingMinutesAnalyzerConfig(model="test-model"),
    )

    document = analyzer.analyze(
        session_id="session-doc",
        session_context=ReportSessionContext(session_id="session-doc"),
        speaker_transcript=[
            SpeakerTranscriptSegment(
                speaker_label="SPEAKER_00",
                start_ms=0,
                end_ms=1000,
                text="오늘은 챗봇 RAG와 회의록 생성 참고 맥락을 점검합니다.",
                confidence=0.95,
            )
        ],
        events=[],
        fallback_document=ReportDocumentV1(title="fallback"),
        reference_context=[
            {
                "source_type": "note",
                "title": "지난 회의 note transcript",
                "heading": "Transcript",
                "session_id": "previous-session",
                "text": "지난 회의에서는 노트 전문 임베딩을 우선하기로 했다.",
            }
        ],
    )

    prompt_payload = json.loads(completion_client.prompt)
    assert document is not None
    assert prompt_payload["RAG 참고 맥락"]["items"][0]["source_type"] == "note"
    assert "전사에 없는 결정/할 일/발언을 새로 만들지 않는다" in (
        prompt_payload["RAG 참고 맥락"]["사용 규칙"]
    )


def test_prepare_report_content_passes_reference_context_to_minutes_analyzer() -> None:
    analyzer = _StubMeetingMinutesAnalyzer()

    prepared = prepare_report_content(
        session_id="session-doc",
        audio_path=None,
        live_events=[],
        canonical_speaker_transcript=[
            SpeakerTranscriptSegment(
                speaker_label="SPEAKER_00",
                start_ms=0,
                end_ms=1200,
                text="회의록 생성에서 기존 노트를 참고 맥락으로 사용합니다.",
                confidence=0.95,
            )
        ],
        event_repository=_EmptyEventRepository(),
        audio_postprocessing_service=None,
        speaker_event_projection_service=None,
        meeting_minutes_analyzer=analyzer,
        meeting_reference_context_service=_StubMeetingReferenceContextService(),
    )

    assert analyzer.received_reference_context is not None
    assert analyzer.received_reference_context[0]["source_type"] == "note"
    assert prepared.analysis_snapshot is not None
    assert prepared.analysis_snapshot["reference_context"] == analyzer.received_reference_context
