"""리포트 영역의 test generation readiness 동작을 검증한다."""
from server.app.domain.models.utterance import Utterance
from server.app.infrastructure.artifacts import LocalArtifactStore
from server.app.services.reports.generation.helpers.generation_readiness import (
    resolve_report_generation_readiness,
)
from server.app.services.reports.refinement import (
    TranscriptCorrectionDocument,
    TranscriptCorrectionItem,
    TranscriptCorrectionStore,
)


class _StubEventRepository:
    def list_by_session(self, session_id, insight_scope=None):
        del session_id, insight_scope
        return []


class _StubUtteranceRepository:
    def __init__(self, utterances):
        self._utterances = list(utterances)

    def list_by_session(self, session_id):
        del session_id
        return list(self._utterances)


class TestReportGenerationReadiness:
    """ReportGenerationReadiness 동작을 검증한다."""
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
