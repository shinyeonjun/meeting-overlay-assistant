"""세션 overview API 테스트."""

from server.app.domain.models.meeting_event import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.domain.shared.enums import EventState, EventType
from server.app.infrastructure.persistence.postgresql.repositories.events import (
    PostgreSQLMeetingEventRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_utterance_repository import (
    PostgreSQLUtteranceRepository,
)
from tests.fixtures.support.sample_inputs import (
    ACTION_TEXT,
    DECISION_TEXT,
    QUESTION_TEXT,
    RISK_TEXT,
    SESSION_TITLE,
    TOPIC_TEXT,
)


class TestOverviewApi:
    """세션 overview 조회 테스트.

    text WebSocket 경로는 live runtime 데이터를 DB에 저장하지 않으므로
    (persist_live_runtime_data=False), 발화/이벤트는 repository로 직접 시드한다.
    """

    def test_세션_overview를_조회하면_이벤트가_유형별로_묶여서_반환된다(
        self,
        client,
        isolated_database,
    ):
        session_id = _create_started_session(client)
        _seed_utterances(
            isolated_database,
            session_id,
            [
                (TOPIC_TEXT, None),
                (RISK_TEXT, None),
                (QUESTION_TEXT, EventType.QUESTION),
                (DECISION_TEXT, None),
                (ACTION_TEXT, None),
            ],
        )

        response = client.get(f"/api/v1/sessions/{session_id}/overview")

        assert response.status_code == 200
        payload = response.json()
        assert payload["session"]["id"] == session_id
        assert payload["current_topic"] == "로그인 / 오류 논의"
        assert len(payload["questions"]) == 1
        assert len(payload["decisions"]) == 0
        assert len(payload["action_items"]) == 0
        assert len(payload["risks"]) == 0
        assert payload["questions"][0]["state"] == "open"
        assert "metrics" in payload
        assert payload["metrics"]["recent_average_latency_ms"] is not None
        assert payload["metrics"]["recent_average_latency_ms"] >= 0
        assert payload["metrics"]["recent_utterance_count_by_source"]["system_audio"] >= 5

    def test_설명_발화가_여러개면_current_topic은_요약값을_반환한다(
        self,
        client,
        isolated_database,
    ):
        session_id = _create_started_session(client)
        _seed_utterances(
            isolated_database,
            session_id,
            [
                ("로그인 오류 원인을 먼저 분석해보죠", None),
                ("로그인 화면에서 세션 만료 오류가 나는 것 같습니다", None),
                ("오류가 사파리 로그인 처리에서 많이 보입니다", None),
            ],
        )

        response = client.get(f"/api/v1/sessions/{session_id}/overview")

        assert response.status_code == 200
        payload = response.json()
        assert payload["current_topic"] == "로그인 / 오류 논의"
        assert payload["metrics"]["recent_utterance_count_by_source"]["system_audio"] >= 3


def _create_started_session(client) -> str:
    create_response = client.post(
        "/api/v1/sessions",
        json={
            "title": SESSION_TITLE,
            "mode": "meeting",
            "source": "system_audio",
        },
    )
    session_id = create_response.json()["id"]
    start_response = client.post(f"/api/v1/sessions/{session_id}/start")
    assert start_response.status_code == 200
    return session_id


def _seed_utterances(
    isolated_database,
    session_id: str,
    items: list[tuple[str, EventType | None]],
) -> None:
    utterance_repository = PostgreSQLUtteranceRepository(isolated_database)
    event_repository = PostgreSQLMeetingEventRepository(isolated_database)

    for index, (text, event_type) in enumerate(items, start=1):
        utterance = utterance_repository.save(
            Utterance.create(
                session_id=session_id,
                seq_num=index,
                start_ms=(index - 1) * 1000,
                end_ms=index * 1000,
                text=text,
                confidence=0.95,
                input_source="system_audio",
                latency_ms=10,
            )
        )
        if event_type is None:
            continue
        event_repository.save(
            MeetingEvent.create(
                session_id=session_id,
                event_type=event_type,
                title=text,
                state=EventState.OPEN,
                source_utterance_id=utterance.id,
                evidence_text=text,
                input_source="system_audio",
            )
        )
