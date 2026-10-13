"""리포트 입력 준비 단계 transcript 보정 테스트."""

from server.app.contexts.insight import MeetingEvent
from server.app.domain.models.utterance import Utterance
from server.app.domain.shared.enums import EventState, EventType
from server.app.infrastructure.artifacts import LocalArtifactStore
from server.app.contexts.reporting import (
    resolve_report_generation_readiness,
)
from server.app.contexts.reporting import (
    TranscriptCorrectionDocument,
    TranscriptCorrectionItem,
    TranscriptCorrectionStore,
)


class _StubEventRepository:
    def __init__(self, events=()):
        self._events = list(events)

    def list_by_session(self, session_id, insight_scope=None):
        del session_id, insight_scope
        return list(self._events)


class _StubUtteranceRepository:
    def __init__(self, utterances):
        self._utterances = list(utterances)

    def list_by_session(self, session_id):
        del session_id
        return list(self._utterances)


class TestReportGenerationReadiness:
    def test_보정_artifact가_있으면_corrected_transcript를_우선_사용한다(self, tmp_path):
        utterance = Utterance.create(
            session_id="session-test",
            seq_num=1,
            start_ms=0,
            end_ms=2000,
            text="큐웬 투 점 오는 괜찮습니다.",
            confidence=0.9,
            speaker_label="SPEAKER_00",
            transcript_source="post_processed",
            processing_job_id="job-test",
        )
        correction_store = TranscriptCorrectionStore(LocalArtifactStore(tmp_path))
        correction_store.save(
            TranscriptCorrectionDocument(
                session_id="session-test",
                source_version=1,
                model="gemma4:e4b",
                items=[
                    TranscriptCorrectionItem(
                        utterance_id=utterance.id,
                        raw_text=utterance.text,
                        corrected_text="Qwen 2.5는 괜찮습니다.",
                        changed=True,
                        risk_flags=[],
                    )
                ],
            )
        )

        readiness = resolve_report_generation_readiness(
            session_id="session-test",
            audio_path=None,
            event_repository=_StubEventRepository(),
            utterance_repository=_StubUtteranceRepository([utterance]),
            transcript_correction_store=correction_store,
        )

        assert readiness.transcript_lines == ["Qwen 2.5는 괜찮습니다."]
        assert readiness.speaker_transcript[0].text == "Qwen 2.5는 괜찮습니다."

    def test_화자_이름이_있으면_리포트_입력의_화자_라벨을_이름으로_바꾼다(self):
        utterances = [
            Utterance.create(
                session_id="session-test",
                seq_num=index,
                start_ms=index * 1000,
                end_ms=index * 1000 + 500,
                text=f"발화 {index}",
                confidence=0.9,
                speaker_label=label,
                transcript_source="post_processed",
            )
            for index, label in enumerate(["SPEAKER_00", "SPEAKER_01", None], start=1)
        ]
        event = MeetingEvent.create(
            session_id="session-test",
            event_type=EventType.ACTION_ITEM,
            title="릴리스 노트 작성",
            state=EventState.OPEN,
            source_utterance_id=None,
            speaker_label="SPEAKER_01",
        )
        unlabeled_event = MeetingEvent.create(
            session_id="session-test",
            event_type=EventType.QUESTION,
            title="로그 이슈 확인",
            state=EventState.OPEN,
            source_utterance_id=None,
        )
        received = {}

        def resolve(session_id, items):
            received["call"] = (session_id, len(items))
            return {"SPEAKER_00": "김민수", "SPEAKER_01": "화자 2", "speaker-unknown": "미분류"}

        readiness = resolve_report_generation_readiness(
            session_id="session-test",
            audio_path=None,
            event_repository=_StubEventRepository([event, unlabeled_event]),
            utterance_repository=_StubUtteranceRepository(utterances),
            speaker_name_resolver=resolve,
        )

        assert received["call"] == ("session-test", 3)
        assert [segment.speaker_label for segment in readiness.speaker_transcript] == [
            "김민수",
            "화자 2",
            "미분류",
        ]
        assert [item.speaker_label for item in readiness.live_events] == ["화자 2", None]

    def test_화자_이름_해석기가_없으면_원래_라벨을_쓴다(self):
        utterance = Utterance.create(
            session_id="session-test",
            seq_num=1,
            start_ms=0,
            end_ms=500,
            text="발화",
            confidence=0.9,
            speaker_label=None,
            transcript_source="post_processed",
        )

        readiness = resolve_report_generation_readiness(
            session_id="session-test",
            audio_path=None,
            event_repository=_StubEventRepository(),
            utterance_repository=_StubUtteranceRepository([utterance]),
        )

        assert readiness.speaker_transcript[0].speaker_label == "speaker-unknown"
