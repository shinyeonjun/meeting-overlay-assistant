"""workspace summary synthesizer 테스트."""

from __future__ import annotations

import json

from server.app.domain.events.meeting_event import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.domain.session import MeetingSession
from server.app.domain.shared.enums import AudioSource, EventState, EventType, SessionMode
from server.app.services.sessions.workspace_summary_synthesizer import (
    LLMWorkspaceSummarySynthesizer,
)


class _RecordingCompletionClient:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def complete(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        response_schema: dict[str, object] | None = None,
        keep_alive: str | None = None,
    ) -> str:
        self.calls.append(
            {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "response_schema": response_schema,
                "keep_alive": keep_alive,
            }
        )
        return self._responses.pop(0)


class TestWorkspaceSummarySynthesizer:
    def test_긴_노트는_계층형_map_reduce를_수행한다(self):
        session = MeetingSession.start(
            title="summary hierarchy 테스트",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        utterances = [
            Utterance.create(
                session_id=session.id,
                seq_num=1,
                start_ms=0,
                end_ms=15000,
                text="로그 오류가 반복되고 있어 먼저 재현 경로를 확인해야 합니다.",
                confidence=0.95,
                input_source="system_audio",
                speaker_label="SPEAKER_00",
            ),
            Utterance.create(
                session_id=session.id,
                seq_num=2,
                start_ms=15000,
                end_ms=30000,
                text="브라우저 캐시와 모바일 환경에서 각각 어떻게 다르게 나타나는지 비교해 보죠.",
                confidence=0.95,
                input_source="system_audio",
                speaker_label="SPEAKER_01",
            ),
            Utterance.create(
                session_id=session.id,
                seq_num=3,
                start_ms=30000,
                end_ms=45000,
                text="이번 주 금요일 발표를 유지하려면 오늘 안에 체크리스트를 정리해야 합니다.",
                confidence=0.95,
                input_source="system_audio",
                speaker_label="SPEAKER_01",
            ),
            Utterance.create(
                session_id=session.id,
                seq_num=4,
                start_ms=45000,
                end_ms=60000,
                text="발표 전에 로그 오류 재현 여부를 다시 확인하고 운영 문서를 업데이트하겠습니다.",
                confidence=0.95,
                input_source="system_audio",
                speaker_label="SPEAKER_02",
            ),
        ]
        events = [
            MeetingEvent.create(
                session_id=session.id,
                event_type=EventType.TOPIC,
                title="로그 오류 대응",
                state=EventState.OPEN,
                source_utterance_id=utterances[0].id,
            ),
            MeetingEvent.create(
                session_id=session.id,
                event_type=EventType.TOPIC,
                title="발표 일정 정리",
                state=EventState.OPEN,
                source_utterance_id=utterances[2].id,
            ),
            MeetingEvent.create(
                session_id=session.id,
                event_type=EventType.DECISION,
                title="이번 주 금요일 발표를 유지한다",
                state=EventState.CONFIRMED,
                source_utterance_id=utterances[2].id,
                speaker_label="SPEAKER_01",
            ),
            MeetingEvent.create(
                session_id=session.id,
                event_type=EventType.ACTION_ITEM,
                title="발표 체크리스트 정리",
                state=EventState.OPEN,
                source_utterance_id=utterances[3].id,
                speaker_label="SPEAKER_02",
            ),
            MeetingEvent.create(
                session_id=session.id,
                event_type=EventType.QUESTION,
                title="로그 오류 재현 조건을 어떻게 고정할지",
                state=EventState.OPEN,
                source_utterance_id=utterances[1].id,
                speaker_label="SPEAKER_01",
            ),
        ]
        client = _RecordingCompletionClient(
            responses=[
                json.dumps(
                    {
                        "meeting_type": "business_meeting",
                        "chunk_summary": ["로그 오류 재현 조건과 확인 범위를 정리했다."],
                        "local_topics": [
                            {
                                "title": "로그 오류 대응",
                                "summary": "로그 오류가 어떤 환경에서 반복되는지 정리했다.",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "meeting_type": "business_meeting",
                        "chunk_summary": ["발표 일정과 사전 준비 작업을 정리했다."],
                        "local_topics": [
                            {
                                "title": "발표 일정 정리",
                                "summary": "발표 일정 유지와 준비 작업을 논의했다.",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "meeting_type": "business_meeting",
                        "topics": [
                            {
                                "chunk_indexes": [0],
                                "title": "로그 오류 대응",
                                "summary": "재현 조건과 확인 범위를 정리한 주제다.",
                            },
                            {
                                "chunk_indexes": [1],
                                "title": "발표 일정 정리",
                                "summary": "발표 일정 유지와 준비 작업을 정리한 주제다.",
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "summary": "로그 오류가 어떤 환경에서 재현되는지 정리했다.",
                        "decisions": [],
                        "next_actions": [],
                        "open_questions": ["로그 오류 재현 조건을 어떻게 고정할지"],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "summary": "이번 주 금요일 발표를 유지하고 준비 작업을 정리했다.",
                        "decisions": ["이번 주 금요일 발표를 유지한다"],
                        "next_actions": [
                            {
                                "title": "발표 체크리스트 정리",
                                "owner": "SPEAKER_02",
                                "due_date": None,
                            }
                        ],
                        "open_questions": [],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "headline": "로그 오류 대응과 발표 일정 정리",
                        "summary": [
                            "이번 회의에서는 로그 오류 재현 조건과 발표 일정 준비를 함께 점검했다.",
                            "발표는 이번 주 금요일로 유지하고 체크리스트를 정리하기로 했다.",
                        ],
                        "decisions": ["이번 주 금요일 발표를 유지한다"],
                        "next_actions": [
                            {
                                "title": "발표 체크리스트 정리",
                                "owner": "SPEAKER_02",
                                "due_date": None,
                            }
                        ],
                        "open_questions": ["로그 오류 재현 조건을 어떻게 고정할지"],
                        "changed_since_last_meeting": [],
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        synthesizer = LLMWorkspaceSummarySynthesizer(
            client,
            model="gemma4:e4b",
            note_max_chars=110,
            chunk_overlap_utterances=0,
            max_chunk_count=4,
        )

        document = synthesizer.synthesize(
            session=session,
            source_version=3,
            utterances=utterances,
            correction_document=None,
            events=events,
        )

        assert len(client.calls) == 6
        assert "구간 회의 내용" in str(client.calls[0]["prompt"])
        assert "구간별 주제 후보" in str(client.calls[2]["prompt"])
        assert "주제별 분석 결과" in str(client.calls[5]["prompt"])
        assert document.headline == "로그 오류 대응과 발표 일정 정리"
        assert document.summary == [
            "이번 회의에서는 로그 오류 재현 조건과 발표 일정 준비를 함께 점검했다.",
            "발표는 이번 주 금요일로 유지하고 체크리스트를 정리하기로 했다.",
        ]
        assert [item.title for item in document.topics] == [
            "로그 오류 대응",
            "발표 일정 정리",
        ]
        assert document.topics[0].start_ms == 0
        assert document.topics[1].start_ms == 30000
        assert document.decisions == ["이번 주 금요일 발표를 유지한다"]
        assert [item.title for item in document.next_actions] == ["발표 체크리스트 정리"]
        assert document.open_questions == ["로그 오류 재현 조건을 어떻게 고정할지"]
