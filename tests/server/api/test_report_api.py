"""회의록 API 테스트."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from server.app.api.http import routes as api_routes
from server.app.domain.events.meeting_event import MeetingEvent
from server.app.domain.models.note_correction_job import NoteCorrectionJob
from server.app.domain.models.report_generation_job import ReportGenerationJob
from server.app.domain.models.session_post_processing_job import SessionPostProcessingJob
from server.app.domain.models.utterance import Utterance
from server.app.domain.shared.enums import EventState, EventType
from server.app.infrastructure.persistence.postgresql.repositories.events import (
    PostgreSQLMeetingEventRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_note_correction_job_repository import (
    PostgreSQLNoteCorrectionJobRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_report_generation_job_repository import (
    PostgreSQLReportGenerationJobRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_session_post_processing_job_repository import (
    PostgreSQLSessionPostProcessingJobRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_report_repository import (
    PostgreSQLReportRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.postgresql_utterance_repository import (
    PostgreSQLUtteranceRepository,
)
from server.app.infrastructure.persistence.postgresql.repositories.session import (
    PostgreSQLSessionRepository,
)
from server.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)
from server.app.services.reports.composition.speaker_event_projection_service import (
    SpeakerAttributedEvent,
)
from server.app.services.reports.core.report_service import ReportService
from tests.fixtures.support.sample_inputs import DECISION_TEXT, RISK_TEXT, SESSION_TITLE


class TestReportApi:
    """회의록 생성과 조회 API를 검증한다."""

    def test_마크다운_회의록_api를_호출하면_markdown_파일을_생성한다(
        self,
        client,
        isolated_database,
    ):
        session_id = _prepare_completed_session(
            client,
            isolated_database,
            [
                {
                    "text": DECISION_TEXT,
                    "event_type": EventType.DECISION,
                    "state": EventState.CONFIRMED,
                },
                {
                    "text": RISK_TEXT,
                    "event_type": EventType.RISK,
                    "state": EventState.OPEN,
                },
            ],
        )

        response = client.post(f"/api/v1/reports/{session_id}/markdown")

        assert response.status_code == 200
        payload = response.json()
        report_content = Path(payload["file_path"]).read_text(encoding="utf-8")
        html_content = Path(payload["html_path"]).read_text(encoding="utf-8")
        document_content = json.loads(
            Path(payload["document_path"]).read_text(encoding="utf-8")
        )
        assert payload["session_id"] == session_id
        assert payload["report_type"] == "markdown"
        assert payload["insight_source"] == "high_precision_audio"
        assert payload["version"] == 1
        assert payload["file_artifact_id"] == f"reports/{session_id}/markdown/v1/report.md"
        assert payload["file_path"].endswith(
            "\\artifacts\\reports\\" + session_id + "\\markdown\\v1\\report.md"
        ) or payload["file_path"].endswith(
            "/artifacts/reports/" + session_id + "/markdown/v1/report.md"
        )
        assert session_id in payload["file_path"]
        assert report_content.startswith(f"# {SESSION_TITLE}")
        assert "## 안건 및 논의" in report_content
        assert "## 결정 사항" in report_content
        assert "## 후속 조치" in report_content
        assert "## 리스크" in report_content
        assert payload["html_path"].endswith(".html")
        assert payload["document_path"].endswith(".document.json")
        assert "회의 요약" in html_content
        assert "안건 및 논의" in html_content
        assert "후속 조치" in html_content
        assert SESSION_TITLE in html_content
        assert DECISION_TEXT in html_content
        metadata = {
            item["label"]: item["value"]
            for item in document_content["document"]["metadata"]
        }
        assert metadata["회의주제"] == SESSION_TITLE
        assert metadata["기록 기준"].startswith("정식 후처리 · 전사")

        source_response = client.get(
            f"/api/v1/reports/{session_id}/{payload['id']}/artifact/source"
        )
        html_response = client.get(
            f"/api/v1/reports/{session_id}/{payload['id']}/artifact/html"
        )
        document_response = client.get(
            f"/api/v1/reports/{session_id}/{payload['id']}/artifact/document"
        )
        assert source_response.status_code == 200
        assert source_response.text.startswith(f"# {SESSION_TITLE}")
        assert html_response.status_code == 200
        assert "회의 요약" in html_response.text
        assert document_response.status_code == 200
        assert document_response.json()["document"]["metadata"][0]["label"] == "회의일자"

    def test_audio_path를_주면_화자_전사와_화자_이벤트_섹션도_생성한다(
        self,
        client,
        tmp_path: Path,
        monkeypatch,
        isolated_database,
    ):
        session_id = _create_session(client)
        wav_path = tmp_path / "sample.wav"
        wav_path.write_bytes(b"placeholder")
        monkeypatch.setattr(
            api_routes.reports,
            "settings",
            replace(api_routes.reports.settings, debug=True),
        )

        report_service = ReportService(
            event_repository=PostgreSQLMeetingEventRepository(isolated_database),
            report_repository=PostgreSQLReportRepository(isolated_database),
            utterance_repository=PostgreSQLUtteranceRepository(isolated_database),
            audio_postprocessing_service=_FakeAudioPostprocessingService(),
            speaker_event_projection_service=_FakeSpeakerEventProjectionService(),
        )
        monkeypatch.setattr(api_routes.reports, "get_report_service", lambda: report_service)

        response = client.post(
            f"/api/v1/reports/{session_id}/markdown",
            params={"audio_path": str(wav_path)},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["insight_source"] == "high_precision_audio"
        assert payload["file_artifact_id"] is None
        assert payload["transcript_path"].endswith(".transcript.md")
        assert payload["analysis_path"].endswith(".analysis.json")
        assert "\\artifacts\\" in payload["transcript_path"] or "/artifacts/" in payload["transcript_path"]
        assert "\\artifacts\\" in payload["analysis_path"] or "/artifacts/" in payload["analysis_path"]
        assert Path(payload["transcript_path"]).exists()
        assert Path(payload["analysis_path"]).exists()
        report_content = Path(payload["file_path"]).read_text(encoding="utf-8")
        assert "## 참고 전사" in report_content
        assert "## 발화자 기반 인사이트" in report_content

    def test_audio_후처리가_실패해도_저장된_canonical_데이터로_fallback_회의록을_생성한다(
        self,
        client,
        tmp_path: Path,
        monkeypatch,
        isolated_database,
    ):
        session_id = _prepare_completed_session(
            client,
            isolated_database,
            [
                {
                    "text": DECISION_TEXT,
                    "event_type": EventType.DECISION,
                    "state": EventState.CONFIRMED,
                }
            ],
        )
        wav_path = tmp_path / "broken.wav"
        wav_path.write_bytes(b"placeholder")
        monkeypatch.setattr(
            api_routes.reports,
            "settings",
            replace(api_routes.reports.settings, debug=True),
        )

        report_service = ReportService(
            event_repository=PostgreSQLMeetingEventRepository(isolated_database),
            report_repository=PostgreSQLReportRepository(isolated_database),
            utterance_repository=PostgreSQLUtteranceRepository(isolated_database),
            audio_postprocessing_service=_BrokenAudioPostprocessingService(),
            speaker_event_projection_service=_FakeSpeakerEventProjectionService(),
        )
        monkeypatch.setattr(api_routes.reports, "get_report_service", lambda: report_service)

        response = client.post(
            f"/api/v1/reports/{session_id}/markdown",
            params={"audio_path": str(wav_path)},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["insight_source"] == "high_precision_audio"
        assert len(payload["speaker_transcript"]) == 1
        assert len(payload["speaker_events"]) == 1
        assert payload["transcript_path"] is not None
        assert payload["analysis_path"] is not None
        analysis_payload = Path(payload["analysis_path"]).read_text(encoding="utf-8")
        assert '"speaker_processing_error": null' in analysis_payload

    def test_debug가_아니면_audio_path는_거부한다(
        self,
        client,
        tmp_path: Path,
        monkeypatch,
    ):
        session_id = _create_session(client)
        wav_path = tmp_path / "sample.wav"
        wav_path.write_bytes(b"placeholder")
        monkeypatch.setattr(
            api_routes.reports,
            "settings",
            replace(api_routes.reports.settings, debug=False),
        )

        response = client.post(
            f"/api/v1/reports/{session_id}/markdown",
            params={"audio_path": str(wav_path)},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == (
            "audio_path 파라미터는 디버그 환경에서만 허용됩니다. audio_artifact_id를 사용하세요."
        )

    def test_audio_path가_없어도_세션_녹음_파일을_자동_참조한다(
        self,
        client,
        tmp_path: Path,
        monkeypatch,
        isolated_database,
    ):
        session_id = _create_session(client)
        wav_path = tmp_path / "recorded.wav"
        wav_path.write_bytes(b"placeholder")

        report_service = ReportService(
            event_repository=PostgreSQLMeetingEventRepository(isolated_database),
            report_repository=PostgreSQLReportRepository(isolated_database),
            utterance_repository=PostgreSQLUtteranceRepository(isolated_database),
            audio_postprocessing_service=_FakeAudioPostprocessingService(),
            speaker_event_projection_service=_FakeSpeakerEventProjectionService(),
        )
        monkeypatch.setattr(api_routes.reports, "get_report_service", lambda: report_service)
        monkeypatch.setattr(
            api_routes.reports,
            "find_session_recording_artifact",
            lambda current_session_id, artifact_store=None: (
                type(
                    "_Artifact",
                    (),
                    {
                        "artifact_id": "recordings/test-session/system_audio.wav",
                        "file_path": wav_path,
                    },
                )()
                if current_session_id == session_id
                else None
            ),
        )

        response = client.post(f"/api/v1/reports/{session_id}/markdown")

        assert response.status_code == 200
        payload = response.json()
        assert payload["insight_source"] == "high_precision_audio"
        assert payload["file_artifact_id"] is None
        assert Path(payload["file_path"]).exists()

    def test_회의록_목록_api가_세션별_회의록_목록을_반환한다(
        self,
        client,
        isolated_database,
    ):
        session_id = _prepare_completed_session(
            client,
            isolated_database,
            [
                {
                    "text": DECISION_TEXT,
                    "event_type": EventType.DECISION,
                    "state": EventState.CONFIRMED,
                }
            ],
        )

        client.post(f"/api/v1/reports/{session_id}/markdown")
        response = client.get(f"/api/v1/reports/{session_id}")

        assert response.status_code == 200
        payload = response.json()
        assert len(payload["items"]) == 1
        assert payload["items"][0]["session_id"] == session_id
        assert payload["items"][0]["report_type"] == "markdown"
        assert payload["items"][0]["insight_source"] == "high_precision_audio"
        assert payload["items"][0]["version"] == 1

    def test_최신_회의록_api가_본문을_포함해서_반환한다(
        self,
        client,
        isolated_database,
    ):
        session_id = _prepare_completed_session(
            client,
            isolated_database,
            [
                {
                    "text": RISK_TEXT,
                    "event_type": EventType.RISK,
                    "state": EventState.OPEN,
                }
            ],
        )

        client.post(f"/api/v1/reports/{session_id}/markdown")
        response = client.get(f"/api/v1/reports/{session_id}/latest")

        assert response.status_code == 200
        payload = response.json()
        assert payload["session_id"] == session_id
        assert payload["report_type"] == "markdown"
        assert payload["insight_source"] == "high_precision_audio"
        assert payload["version"] == 1
        assert "## 리스크" in payload["content"]

    def test_마크다운_회의록_파일이_바뀌면_최신_조회는_파일_본문을_반환한다(
        self,
        client,
        isolated_database,
    ):
        session_id = _prepare_completed_session(
            client,
            isolated_database,
            [
                {
                    "text": RISK_TEXT,
                    "event_type": EventType.RISK,
                    "state": EventState.OPEN,
                }
            ],
        )

        create_response = client.post(f"/api/v1/reports/{session_id}/markdown")
        report_path = Path(create_response.json()["file_path"])
        report_path.write_text("# tampered", encoding="utf-8")

        latest_response = client.get(f"/api/v1/reports/{session_id}/latest")

        assert latest_response.status_code == 200
        payload = latest_response.json()
        assert payload["content"] == "# tampered"

    def test_최신_회의록이_없으면_404를_반환한다(self, client):
        session_id = _create_session(client)

        response = client.get(f"/api/v1/reports/{session_id}/latest")

        assert response.status_code == 404
        assert response.json()["detail"] == "회의록이 아직 생성되지 않았습니다."

    def test_pdf_회의록_api를_호출하면_pdf_파일과_source_markdown을_반환한다(
        self,
        client,
        isolated_database,
    ):
        session_id = _prepare_completed_session(
            client,
            isolated_database,
            [
                {
                    "text": DECISION_TEXT,
                    "event_type": EventType.DECISION,
                    "state": EventState.CONFIRMED,
                }
            ],
        )

        response = client.post(f"/api/v1/reports/{session_id}/pdf")

        assert response.status_code == 200
        payload = response.json()
        pdf_path = Path(payload["file_path"])
        assert payload["report_type"] == "pdf"
        assert payload["insight_source"] == "high_precision_audio"
        assert payload["version"] == 1
        assert payload["file_artifact_id"] == f"reports/{session_id}/pdf/v1/report.pdf"
        assert payload["file_path"].endswith(
            "\\artifacts\\reports\\" + session_id + "\\pdf\\v1\\report.pdf"
        ) or payload["file_path"].endswith(
            "/artifacts/reports/" + session_id + "/pdf/v1/report.pdf"
        )
        assert session_id in payload["file_path"]
        assert pdf_path.exists()
        assert pdf_path.read_bytes().startswith(b"%PDF")
        assert payload["source_markdown"].startswith(f"# {SESSION_TITLE}")
        assert "## 안건 및 논의" in payload["source_markdown"]
        assert "## 결정 사항" in payload["source_markdown"]
        assert "## 후속 조치" in payload["source_markdown"]
        assert payload["html_path"].endswith(".html")
        assert payload["document_path"].endswith(".document.json")
        assert Path(payload["html_path"]).exists()
        assert Path(payload["document_path"]).exists()
        download_response = client.get(
            f"/api/v1/reports/{session_id}/{payload['id']}/artifact/source",
            params={"download": "true"},
        )
        assert download_response.status_code == 200
        assert download_response.headers["content-type"].startswith("application/pdf")
        assert "attachment" in download_response.headers["content-disposition"]
        assert download_response.content.startswith(b"%PDF")

    def test_최신_회의록이_pdf면_content는_null이다(
        self,
        client,
        isolated_database,
    ):
        session_id = _prepare_completed_session(
            client,
            isolated_database,
            [
                {
                    "text": DECISION_TEXT,
                    "event_type": EventType.DECISION,
                    "state": EventState.CONFIRMED,
                }
            ],
        )

        client.post(f"/api/v1/reports/{session_id}/pdf")
        latest_response = client.get(f"/api/v1/reports/{session_id}/latest")

        assert latest_response.status_code == 200
        payload = latest_response.json()
        assert payload["report_type"] == "pdf"
        assert payload["insight_source"] == "high_precision_audio"
        assert payload["version"] == 1
        assert payload["content"] is None

    def test_report_id로_개별_회의록을_조회할_수_있다(
        self,
        client,
        isolated_database,
    ):
        session_id = _prepare_completed_session(
            client,
            isolated_database,
            [
                {
                    "text": RISK_TEXT,
                    "event_type": EventType.RISK,
                    "state": EventState.OPEN,
                }
            ],
        )

        create_report_response = client.post(f"/api/v1/reports/{session_id}/markdown")
        report_id = create_report_response.json()["id"]

        response = client.get(f"/api/v1/reports/{session_id}/{report_id}")

        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == report_id
        assert payload["session_id"] == session_id
        assert payload["insight_source"] == "high_precision_audio"
        assert payload["version"] == 1
        assert "## 리스크" in payload["content"]

    def test_report_id_조회도_파일_본문을_우선_사용한다(
        self,
        client,
        isolated_database,
    ):
        session_id = _prepare_completed_session(
            client,
            isolated_database,
            [
                {
                    "text": DECISION_TEXT,
                    "event_type": EventType.DECISION,
                    "state": EventState.CONFIRMED,
                }
            ],
        )

        create_report_response = client.post(f"/api/v1/reports/{session_id}/markdown")
        payload = create_report_response.json()
        report_id = payload["id"]
        report_path = Path(payload["file_path"])
        report_path.write_text("# overwritten", encoding="utf-8")

        response = client.get(f"/api/v1/reports/{session_id}/{report_id}")

        assert response.status_code == 200
        assert response.json()["content"] == "# overwritten"

    def test_final_status는_세션이_진행중이면_pending이다(self, client):
        session_id = _create_session(client)

        response = client.get(f"/api/v1/reports/{session_id}/final-status")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "pending"
        assert payload["pipeline_stage"] == "live"
        assert payload["post_processing_status"] == "not_started"
        assert payload["report_count"] == 0
        assert payload["latest_report_id"] is None

    def test_세션이_종료되면_final_status가_post_processing_pending상태다(self, client):
        session_id = _create_session(client)
        client.post(f"/api/v1/sessions/{session_id}/end")

        response = client.get(f"/api/v1/reports/{session_id}/final-status")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "pending"
        assert payload["pipeline_stage"] == "post_processing"
        assert payload["post_processing_status"] == "queued"
        assert payload["report_count"] == 0
        assert payload["latest_report_type"] is None

    def test_세션이_종료돼도_회의록_job은_자동_생성되지_않는다(self, client):
        session_id = _create_session(client)

        end_response = client.post(f"/api/v1/sessions/{session_id}/end")
        assert end_response.status_code == 200

        response = client.get(f"/api/v1/reports/{session_id}/job")

        assert response.status_code == 404
        assert response.json()["detail"] == "회의록 생성 job이 없습니다."

    def test_세션이_종료되면_명시적으로_report_job을_생성할_수_있다(self, client):
        session_id = _create_session(client)

        end_response = client.post(f"/api/v1/sessions/{session_id}/end")
        assert end_response.status_code == 200

        create_response = client.post(f"/api/v1/reports/{session_id}/job")

        assert create_response.status_code == 200
        payload = create_response.json()
        assert payload["session_id"] == session_id
        assert payload["status"] == "pending"
        assert payload["recording_artifact_id"] is None
        assert payload["recording_path"] is None

    def test_inline_report_job은_녹음과_정식데이터가_없으면_failed로_정리된다(
        self,
        client,
    ):
        session_id = _create_session(client)

        end_response = client.post(f"/api/v1/sessions/{session_id}/end")
        assert end_response.status_code == 200

        create_response = client.post(f"/api/v1/reports/{session_id}/job")
        assert create_response.status_code == 200

        job_response = client.get(f"/api/v1/reports/{session_id}/job")

        assert job_response.status_code == 200
        payload = job_response.json()
        assert payload["status"] == "failed"
        assert payload["error_message"] == (
            "회의록 생성에 필요한 녹음 파일 또는 저장된 transcript/event가 없습니다."
        )

    def test_inline_report_job은_정식_transcript가_있으면_완료된다(
        self,
        client,
        isolated_database,
    ):
        session_id = _create_session(client)
        client.post(f"/api/v1/sessions/{session_id}/end")
        _seed_canonical_inputs(
            isolated_database,
            session_id,
            [{"text": "이번 주 고객 피드백을 먼저 정리하겠습니다."}],
        )
        _mark_post_processing_completed(isolated_database, session_id)

        create_response = client.post(f"/api/v1/reports/{session_id}/job")
        assert create_response.status_code == 200

        job_response = client.get(f"/api/v1/reports/{session_id}/job")
        assert job_response.status_code == 200
        payload = job_response.json()
        assert payload["status"] == "completed"
        assert payload["markdown_report_id"] is not None

        report_response = client.get(
            f"/api/v1/reports/{session_id}/{payload['markdown_report_id']}"
        )
        assert report_response.status_code == 200
        report_payload = report_response.json()
        assert report_payload["report_type"] == "markdown"
        assert report_payload["content"] is not None

    def test_세션이_진행중이면_report_job_생성을_거부한다(self, client):
        session_id = _create_session(client)

        response = client.post(f"/api/v1/reports/{session_id}/job")

        assert response.status_code == 409
        assert response.json()["detail"] == "회의록 생성은 회의 종료 후에만 요청할 수 있습니다."

    def test_final_status는_회의록_파일이_사라지면_회의록_재생성_대기상태다(
        self,
        client,
        isolated_database,
    ):
        session_id = _prepare_completed_session(
            client,
            isolated_database,
            [
                {
                    "text": DECISION_TEXT,
                    "event_type": EventType.DECISION,
                    "state": EventState.CONFIRMED,
                }
            ],
        )

        report_response = client.post(f"/api/v1/reports/{session_id}/markdown")
        report_path = Path(report_response.json()["file_path"])
        report_path.unlink(missing_ok=True)

        response = client.get(f"/api/v1/reports/{session_id}/final-status")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "pending"
        assert payload["pipeline_stage"] == "report_generation"
        assert payload["report_count"] == 1

    def test_usable_report가_있어도_최신_재생성_실패면_final_status는_failed다(
        self,
        client,
        isolated_database,
    ):
        session_id = _prepare_completed_session(
            client,
            isolated_database,
            [
                {
                    "text": DECISION_TEXT,
                    "event_type": EventType.DECISION,
                    "state": EventState.CONFIRMED,
                }
            ],
        )

        report_response = client.post(f"/api/v1/reports/{session_id}/markdown")
        assert report_response.status_code == 200

        job_repository = PostgreSQLReportGenerationJobRepository(isolated_database)
        failed_job = job_repository.save(
            ReportGenerationJob.create_pending(
                session_id=session_id,
                recording_artifact_id=None,
                recording_path=None,
                requested_by_user_id=None,
            ).mark_failed("worker unavailable")
        )

        response = client.get(f"/api/v1/reports/{session_id}/final-status")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "failed"
        assert payload["pipeline_stage"] == "report_generation"
        assert payload["warning_reason"] == "latest_regeneration_failed"
        assert payload["latest_job_status"] == failed_job.status
        assert payload["latest_job_error_message"] == "worker unavailable"

    def test_usable_report가_있어도_post_processing이_queued면_final_status는_pending이다(
        self,
        client,
        isolated_database,
    ):
        session_id = _prepare_completed_session(
            client,
            isolated_database,
            [
                {
                    "text": DECISION_TEXT,
                    "event_type": EventType.DECISION,
                    "state": EventState.CONFIRMED,
                }
            ],
        )

        report_response = client.post(f"/api/v1/reports/{session_id}/markdown")
        assert report_response.status_code == 200

        session_repository = PostgreSQLSessionRepository(isolated_database)
        session = session_repository.get_by_id(session_id)
        assert session is not None
        session_repository.save(session.queue_post_processing())

        response = client.get(f"/api/v1/reports/{session_id}/final-status")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "pending"
        assert payload["pipeline_stage"] == "post_processing"
        assert payload["post_processing_status"] == "queued"

    def test_usable_report가_있어도_report_job이_pending이면_final_status는_pending이다(
        self,
        client,
        isolated_database,
    ):
        session_id = _prepare_completed_session(
            client,
            isolated_database,
            [
                {
                    "text": DECISION_TEXT,
                    "event_type": EventType.DECISION,
                    "state": EventState.CONFIRMED,
                }
            ],
        )

        report_response = client.post(f"/api/v1/reports/{session_id}/markdown")
        assert report_response.status_code == 200

        job_repository = PostgreSQLReportGenerationJobRepository(isolated_database)
        pending_job = job_repository.save(
            ReportGenerationJob.create_pending(
                session_id=session_id,
                recording_artifact_id=None,
                recording_path=None,
                requested_by_user_id=None,
            )
        )

        response = client.get(f"/api/v1/reports/{session_id}/final-status")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "pending"
        assert payload["pipeline_stage"] == "report_generation"
        assert payload["latest_job_status"] == pending_job.status
        assert payload["warning_reason"] == "latest_regeneration_pending"

    def test_long_pending_job이_있고_usable_report가_없으면_final_status는_pending이다(
        self,
        client,
        isolated_database,
    ):
        session_id = _create_session(client)
        client.post(f"/api/v1/sessions/{session_id}/end")
        _mark_post_processing_completed(isolated_database, session_id)

        job_repository = PostgreSQLReportGenerationJobRepository(isolated_database)
        job_repository.save(
            ReportGenerationJob.create_pending(
                session_id=session_id,
                recording_artifact_id=None,
                recording_path=None,
                requested_by_user_id=None,
            )
        )

        response = client.get(f"/api/v1/reports/{session_id}/final-status")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "pending"
        assert payload["pipeline_stage"] == "report_generation"
        assert payload["latest_job_status"] == "pending"
        assert payload["warning_reason"] is None

    def test_final_status는_세션이_없으면_404다(self, client):
        response = client.get("/api/v1/reports/session-not-found/final-status")

        assert response.status_code == 404
        assert response.json()["detail"] == "세션을 찾을 수 없습니다."

    def test_회의록_재생성_api는_새_버전_markdown과_pdf를_만든다(
        self,
        client,
        isolated_database,
    ):
        session_id = _prepare_completed_session(
            client,
            isolated_database,
            [
                {
                    "text": DECISION_TEXT,
                    "event_type": EventType.DECISION,
                    "state": EventState.CONFIRMED,
                }
            ],
        )

        first_markdown = client.post(f"/api/v1/reports/{session_id}/markdown")
        first_pdf = client.post(f"/api/v1/reports/{session_id}/pdf")

        assert first_markdown.status_code == 200
        assert first_pdf.status_code == 200

        regenerate_response = client.post(f"/api/v1/reports/{session_id}/regenerate")

        assert regenerate_response.status_code == 200
        payload = regenerate_response.json()
        assert payload["session_id"] == session_id
        assert len(payload["items"]) == 2
        assert {
            (item["report_type"], item["version"], item["insight_source"])
            for item in payload["items"]
        } == {
            ("markdown", 2, "high_precision_audio"),
            ("pdf", 2, "high_precision_audio"),
        }
        document_payloads = []
        html_payloads = []
        for item in payload["items"]:
            report_path = Path(item["file_path"])
            document_path = report_path.parent / "artifacts" / f"{report_path.stem}.document.json"
            html_path = report_path.parent / "artifacts" / f"{report_path.stem}.html"
            assert document_path.exists()
            assert html_path.exists()
            document_payloads.append(json.loads(document_path.read_text(encoding="utf-8")))
            html_payloads.append(html_path.read_text(encoding="utf-8"))
        assert document_payloads[0] == document_payloads[1]
        assert html_payloads[0] == html_payloads[1]

        reports_response = client.get(f"/api/v1/reports/{session_id}")
        reports_payload = reports_response.json()
        assert len(reports_payload["items"]) == 4

    def test_confirmed_decision_is_included_in_final_report(
        self,
        client,
        isolated_database,
    ):
        session_id = _create_session(client)
        client.post(f"/api/v1/sessions/{session_id}/end")
        _seed_canonical_inputs(
            isolated_database,
            session_id,
            [
                {
                    "text": "후보 결정",
                    "event_type": EventType.DECISION,
                    "state": EventState.CONFIRMED,
                    "title": "이전 결정",
                },
                {
                    "text": "확정 결정",
                    "event_type": EventType.DECISION,
                    "state": EventState.CONFIRMED,
                    "title": "확정 결정",
                },
            ],
        )
        _mark_post_processing_completed(isolated_database, session_id)

        response = client.post(f"/api/v1/reports/{session_id}/markdown")

        assert response.status_code == 200
        content = response.json()["content"]
        assert "확정 결정" in content
        assert "이전 결정" in content

    def test_post_processing_stalled_job은_final_status를_failed로_내린다(
        self,
        client,
        isolated_database,
    ):
        session_id = _create_session(client)
        client.post(f"/api/v1/sessions/{session_id}/end")

        session_repository = PostgreSQLSessionRepository(isolated_database)
        session = session_repository.get_by_id(session_id)
        assert session is not None
        session_repository.save(session.mark_post_processing_started())

        job_repository = PostgreSQLSessionPostProcessingJobRepository(isolated_database)
        job_repository.save(
            SessionPostProcessingJob.create_pending(
                session_id=session_id,
                recording_artifact_id=None,
                recording_path=None,
            ).mark_processing(
                claimed_by_worker_id="worker-stalled",
                lease_expires_at="2026-04-12T00:00:00+00:00",
                started_at="2026-04-12T00:00:00+00:00",
            )
        )

        response = client.get(f"/api/v1/reports/{session_id}/final-status")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "failed"
        assert payload["pipeline_stage"] == "post_processing"
        assert payload["warning_reason"] == "post_processing_stalled"

    def test_note_correction_stalled_job은_final_status를_failed로_내린다(
        self,
        client,
        isolated_database,
    ):
        session_id = _create_session(client)
        client.post(f"/api/v1/sessions/{session_id}/end")
        _seed_canonical_inputs(
            isolated_database,
            session_id,
            [{"text": "회의 내용을 정리합니다."}],
        )
        _mark_post_processing_completed(isolated_database, session_id)

        note_repository = PostgreSQLNoteCorrectionJobRepository(isolated_database)
        note_repository.save(
            NoteCorrectionJob.create_pending(
                session_id=session_id,
                source_version=1,
            ).mark_processing(
                claimed_by_worker_id="worker-stalled",
                lease_expires_at="2026-04-12T00:00:00+00:00",
                started_at="2026-04-12T00:00:00+00:00",
            )
        )

        response = client.get(f"/api/v1/reports/{session_id}/final-status")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "failed"
        assert payload["pipeline_stage"] == "note_correction"
        assert payload["warning_reason"] == "note_correction_stalled"

    def test_report_generation_stalled_job은_final_status를_failed로_내린다(
        self,
        client,
        isolated_database,
    ):
        session_id = _create_session(client)
        client.post(f"/api/v1/sessions/{session_id}/end")
        _seed_canonical_inputs(
            isolated_database,
            session_id,
            [{"text": "회의 내용을 정리합니다."}],
        )
        _mark_post_processing_completed(isolated_database, session_id)

        job_repository = PostgreSQLReportGenerationJobRepository(isolated_database)
        job_repository.save(
            ReportGenerationJob.create_pending(
                session_id=session_id,
                recording_artifact_id=None,
                recording_path=None,
                requested_by_user_id=None,
            ).mark_processing(
                claimed_by_worker_id="worker-stalled",
                lease_expires_at="2026-04-12T00:00:00+00:00",
                started_at="2026-04-12T00:00:00+00:00",
            )
        )

        response = client.get(f"/api/v1/reports/{session_id}/final-status")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "failed"
        assert payload["pipeline_stage"] == "report_generation"
        assert payload["warning_reason"] == "report_generation_stalled"


def _create_session(client) -> str:
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


def _prepare_completed_session(
    client,
    isolated_database,
    items: list[dict[str, object]],
) -> str:
    session_id = _create_session(client)
    end_response = client.post(f"/api/v1/sessions/{session_id}/end")
    assert end_response.status_code == 200
    _seed_canonical_inputs(isolated_database, session_id, items)
    _mark_post_processing_completed(isolated_database, session_id)
    return session_id


def _seed_canonical_inputs(
    isolated_database,
    session_id: str,
    items: list[dict[str, object]],
) -> None:
    utterance_repository = PostgreSQLUtteranceRepository(isolated_database)
    event_repository = PostgreSQLMeetingEventRepository(isolated_database)

    for index, item in enumerate(items, start=1):
        utterance = utterance_repository.save(
            Utterance.create(
                session_id=session_id,
                seq_num=index,
                start_ms=(index - 1) * 1000,
                end_ms=index * 1000,
                text=str(item["text"]),
                confidence=0.95,
                speaker_label="SPEAKER_00",
                transcript_source="post_processed",
            )
        )
        event_type = item.get("event_type")
        if event_type is None:
            continue
        event_repository.save(
            MeetingEvent.create(
                session_id=session_id,
                event_type=event_type,
                title=str(item.get("title", item["text"])),
                state=item.get("state", EventState.OPEN),
                source_utterance_id=utterance.id,
                evidence_text=utterance.text,
                speaker_label=utterance.speaker_label,
                input_source=utterance.input_source,
                insight_scope="finalized",
                event_source="post_processed",
                finalized_at_ms=index,
            )
        )

def _mark_post_processing_completed(isolated_database, session_id: str) -> None:
    session_repository = PostgreSQLSessionRepository(isolated_database)
    session = session_repository.get_by_id(session_id)
    assert session is not None
    session_repository.save(session.mark_post_processing_completed())


class _FakeAudioPostprocessingService:
    def build_speaker_transcript(self, audio_path: Path):
        return [
            SpeakerTranscriptSegment(
                speaker_label="speaker-unknown",
                start_ms=0,
                end_ms=1000,
                text=f"전처리 전사: {audio_path.name}",
                confidence=0.91,
            )
        ]


class _BrokenAudioPostprocessingService:
    def build_speaker_transcript(self, audio_path: Path):
        raise RuntimeError(f"pyannote worker failed for {audio_path.name}")


class _FakeSpeakerEventProjectionService:
    def project(self, session_id: str, speaker_transcript: list[SpeakerTranscriptSegment]):
        segment = speaker_transcript[0]
        return [
            SpeakerAttributedEvent(
                speaker_label="SPEAKER_00",
                event=MeetingEvent.create(
                    session_id=session_id,
                    event_type=EventType.QUESTION,
                    title=segment.text,
                    body=None,
                    state=EventState.OPEN,
                    source_utterance_id="utt-1",
                ),
            )
        ]
