"""리포트 API 테스트."""

from __future__ import annotations

from pathlib import Path

from backend.app.api.http import routes as api_routes
from backend.app.domain.models.meeting_event import MeetingEvent
from backend.app.domain.models.utterance import Utterance
from backend.app.domain.shared.enums import EventPriority, EventState, EventType
from backend.app.infrastructure.persistence.sqlite.repositories.meeting_event_repository import (
    SQLiteMeetingEventRepository,
)
from backend.app.infrastructure.persistence.sqlite.repositories.report_repository import (
    SQLiteReportRepository,
)
from backend.app.infrastructure.persistence.sqlite.repositories.utterance_repository import (
    SQLiteUtteranceRepository,
)
from backend.app.services.reports.audio.audio_postprocessing_service import (
    SpeakerTranscriptSegment,
)
from backend.app.services.reports.composition.markdown_report_builder import (
    MarkdownReportBuilder,
)
from backend.app.services.reports.composition.speaker_event_projection_service import (
    SpeakerAttributedEvent,
)
from backend.app.services.reports.core.report_service import ReportService
from backend.app.services.reports.refinement.structured_markdown_report_refiner import (
    StructuredMarkdownReportRefiner,
)
from tests.support.sample_inputs import DECISION_TEXT, RISK_TEXT, SESSION_TITLE


class TestReportApi:
    """리포트 생성과 조회 API를 검증한다."""

    def test_마크다운_리포트_api를_호출하면_markdown_파일을_생성한다(self, client):
        session_id = _create_session(client)

        with client.websocket_connect(f"/api/v1/ws/text/{session_id}") as websocket:
            for text in (DECISION_TEXT, RISK_TEXT):
                websocket.send_text(text)
                websocket.receive_json()

        response = client.post(f"/api/v1/reports/{session_id}/markdown")

        assert response.status_code == 200
        payload = response.json()
        report_content = Path(payload["file_path"]).read_text(encoding="utf-8")
        assert payload["session_id"] == session_id
        assert payload["report_type"] == "markdown"
        assert payload["insight_source"] == "live_fallback"
        assert payload["version"] == 1
        assert payload["file_path"].endswith("\\markdown.v1.md") or payload["file_path"].endswith("/markdown.v1.md")
        assert session_id in payload["file_path"]
        assert report_content.startswith("# 회의 리포트")
        assert "## 결정 사항" in report_content
        assert "## 리스크" in report_content

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

        report_service = ReportService(
            event_repository=SQLiteMeetingEventRepository(isolated_database),
            report_repository=SQLiteReportRepository(isolated_database),
            markdown_report_builder=MarkdownReportBuilder(),
            audio_postprocessing_service=_FakeAudioPostprocessingService(),
            speaker_event_projection_service=_FakeSpeakerEventProjectionService(),
            report_refiner=StructuredMarkdownReportRefiner(),
        )
        monkeypatch.setattr(api_routes.reports, "get_report_service", lambda: report_service)

        response = client.post(
            f"/api/v1/reports/{session_id}/markdown",
            params={"audio_path": str(wav_path)},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["insight_source"] == "high_precision_audio"
        assert payload["transcript_path"].endswith(".transcript.md")
        assert payload["analysis_path"].endswith(".analysis.json")
        assert "\\artifacts\\" in payload["transcript_path"] or "/artifacts/" in payload["transcript_path"]
        assert "\\artifacts\\" in payload["analysis_path"] or "/artifacts/" in payload["analysis_path"]
        assert Path(payload["transcript_path"]).exists()
        assert Path(payload["analysis_path"]).exists()
        report_content = Path(payload["file_path"]).read_text(encoding="utf-8")
        assert "## 참고 전사" in report_content
        assert "## 발화자 기반 인사이트" in report_content

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
            event_repository=SQLiteMeetingEventRepository(isolated_database),
            report_repository=SQLiteReportRepository(isolated_database),
            markdown_report_builder=MarkdownReportBuilder(),
            audio_postprocessing_service=_FakeAudioPostprocessingService(),
            speaker_event_projection_service=_FakeSpeakerEventProjectionService(),
            report_refiner=StructuredMarkdownReportRefiner(),
        )
        monkeypatch.setattr(api_routes.reports, "get_report_service", lambda: report_service)
        monkeypatch.setattr(
            api_routes.reports,
            "find_session_recording_path",
            lambda current_session_id: wav_path if current_session_id == session_id else None,
        )

        response = client.post(f"/api/v1/reports/{session_id}/markdown")

        assert response.status_code == 200
        payload = response.json()
        assert payload["insight_source"] == "high_precision_audio"
        assert Path(payload["file_path"]).exists()

    def test_리포트_목록_api가_세션별_리포트_목록을_반환한다(self, client):
        session_id = _create_session(client)

        with client.websocket_connect(f"/api/v1/ws/text/{session_id}") as websocket:
            websocket.send_text(DECISION_TEXT)
            websocket.receive_json()

        client.post(f"/api/v1/reports/{session_id}/markdown")
        response = client.get(f"/api/v1/reports/{session_id}")

        assert response.status_code == 200
        payload = response.json()
        assert len(payload["items"]) == 1
        assert payload["items"][0]["session_id"] == session_id
        assert payload["items"][0]["report_type"] == "markdown"
        assert payload["items"][0]["insight_source"] == "live_fallback"
        assert payload["items"][0]["version"] == 1

    def test_최신_리포트_api가_본문을_포함해서_반환한다(self, client):
        session_id = _create_session(client)

        with client.websocket_connect(f"/api/v1/ws/text/{session_id}") as websocket:
            websocket.send_text(RISK_TEXT)
            websocket.receive_json()

        client.post(f"/api/v1/reports/{session_id}/markdown")
        response = client.get(f"/api/v1/reports/{session_id}/latest")

        assert response.status_code == 200
        payload = response.json()
        assert payload["session_id"] == session_id
        assert payload["report_type"] == "markdown"
        assert payload["insight_source"] == "live_fallback"
        assert payload["version"] == 1
        assert "## 리스크" in payload["content"]

    def test_마크다운_리포트_파일이_바뀌어도_최신_조회는_db_스냅샷을_반환한다(self, client):
        session_id = _create_session(client)

        with client.websocket_connect(f"/api/v1/ws/text/{session_id}") as websocket:
            websocket.send_text(RISK_TEXT)
            websocket.receive_json()

        create_response = client.post(f"/api/v1/reports/{session_id}/markdown")
        report_path = Path(create_response.json()["file_path"])
        original_content = report_path.read_text(encoding="utf-8")
        report_path.write_text("# tampered", encoding="utf-8")

        latest_response = client.get(f"/api/v1/reports/{session_id}/latest")

        assert latest_response.status_code == 200
        payload = latest_response.json()
        assert payload["content"] == original_content

    def test_최신_리포트가_없으면_404를_반환한다(self, client):
        session_id = _create_session(client)

        response = client.get(f"/api/v1/reports/{session_id}/latest")

        assert response.status_code == 404
        assert response.json()["detail"] == "리포트가 아직 생성되지 않았습니다."

    def test_pdf_리포트_api를_호출하면_pdf_파일과_source_markdown을_반환한다(self, client):
        session_id = _create_session(client)

        with client.websocket_connect(f"/api/v1/ws/text/{session_id}") as websocket:
            websocket.send_text(DECISION_TEXT)
            websocket.receive_json()

        response = client.post(f"/api/v1/reports/{session_id}/pdf")

        assert response.status_code == 200
        payload = response.json()
        pdf_path = Path(payload["file_path"])
        assert payload["report_type"] == "pdf"
        assert payload["insight_source"] == "live_fallback"
        assert payload["version"] == 1
        assert payload["file_path"].endswith("\\pdf.v1.pdf") or payload["file_path"].endswith("/pdf.v1.pdf")
        assert session_id in payload["file_path"]
        assert pdf_path.exists()
        assert pdf_path.read_bytes().startswith(b"%PDF")
        assert payload["source_markdown"].startswith("# 회의 리포트")
        assert "## 결정 사항" in payload["source_markdown"]

    def test_최신_리포트가_pdf면_content는_null이다(self, client):
        session_id = _create_session(client)

        with client.websocket_connect(f"/api/v1/ws/text/{session_id}") as websocket:
            websocket.send_text(DECISION_TEXT)
            websocket.receive_json()

        client.post(f"/api/v1/reports/{session_id}/pdf")
        latest_response = client.get(f"/api/v1/reports/{session_id}/latest")

        assert latest_response.status_code == 200
        payload = latest_response.json()
        assert payload["report_type"] == "pdf"
        assert payload["insight_source"] == "live_fallback"
        assert payload["version"] == 1
        assert payload["content"] is None

    def test_report_id로_개별_리포트를_조회할_수_있다(self, client):
        session_id = _create_session(client)

        with client.websocket_connect(f"/api/v1/ws/text/{session_id}") as websocket:
            websocket.send_text(RISK_TEXT)
            websocket.receive_json()

        create_report_response = client.post(f"/api/v1/reports/{session_id}/markdown")
        report_id = create_report_response.json()["id"]

        response = client.get(f"/api/v1/reports/{session_id}/{report_id}")

        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == report_id
        assert payload["session_id"] == session_id
        assert payload["insight_source"] == "live_fallback"
        assert payload["version"] == 1
        assert "## 리스크" in payload["content"]

    def test_report_id_조회도_db_스냅샷을_우선_사용한다(self, client):
        session_id = _create_session(client)

        with client.websocket_connect(f"/api/v1/ws/text/{session_id}") as websocket:
            websocket.send_text(DECISION_TEXT)
            websocket.receive_json()

        create_report_response = client.post(f"/api/v1/reports/{session_id}/markdown")
        payload = create_report_response.json()
        report_id = payload["id"]
        report_path = Path(payload["file_path"])
        original_content = report_path.read_text(encoding="utf-8")
        report_path.write_text("# overwritten", encoding="utf-8")

        response = client.get(f"/api/v1/reports/{session_id}/{report_id}")

        assert response.status_code == 200
        assert response.json()["content"] == original_content

    def test_final_status는_세션이_진행중이면_pending이다(self, client):
        session_id = _create_session(client)

        response = client.get(f"/api/v1/reports/{session_id}/final-status")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "pending"
        assert payload["report_count"] == 0
        assert payload["latest_report_id"] is None

    def test_세션이_종료되면_final_status가_processing이다(self, client):
        session_id = _create_session(client)
        client.post(f"/api/v1/sessions/{session_id}/end")

        response = client.get(f"/api/v1/reports/{session_id}/final-status")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "processing"
        assert payload["report_count"] == 0
        assert payload["latest_report_type"] is None

    def test_final_status는_리포트_파일이_사라지면_failed다(self, client):
        session_id = _create_session(client)

        with client.websocket_connect(f"/api/v1/ws/text/{session_id}") as websocket:
            websocket.send_text(DECISION_TEXT)
            websocket.receive_json()

        report_response = client.post(f"/api/v1/reports/{session_id}/markdown")
        report_path = Path(report_response.json()["file_path"])
        report_path.unlink(missing_ok=True)

        response = client.get(f"/api/v1/reports/{session_id}/final-status")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "failed"
        assert payload["report_count"] == 1

    def test_final_status는_세션이_없으면_404다(self, client):
        response = client.get("/api/v1/reports/session-not-found/final-status")

        assert response.status_code == 404
        assert response.json()["detail"] == "세션을 찾을 수 없습니다."

    def test_리포트_재생성_api는_새_버전_markdown과_pdf를_만든다(self, client):
        session_id = _create_session(client)

        with client.websocket_connect(f"/api/v1/ws/text/{session_id}") as websocket:
            websocket.send_text(DECISION_TEXT)
            websocket.receive_json()

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
            ("markdown", 2, "live_fallback"),
            ("pdf", 2, "live_fallback"),
        }

        reports_response = client.get(f"/api/v1/reports/{session_id}")
        reports_payload = reports_response.json()
        assert len(reports_payload["items"]) == 4

    def test_candidate_decision_is_excluded_from_final_report(self, client, isolated_database):
        session_id = _create_session(client)
        repository = SQLiteMeetingEventRepository(isolated_database)
        utterance_repository = SQLiteUtteranceRepository(isolated_database)
        candidate_utterance = utterance_repository.save(
            Utterance.create(
                session_id=session_id,
                seq_num=1,
                start_ms=0,
                end_ms=1000,
                text="후보 결정",
                confidence=0.95,
            )
        )
        confirmed_utterance = utterance_repository.save(
            Utterance.create(
                session_id=session_id,
                seq_num=2,
                start_ms=1000,
                end_ms=2000,
                text="확정 결정",
                confidence=0.95,
            )
        )
        repository.save(
            MeetingEvent.create(
                session_id=session_id,
                event_type=EventType.DECISION,
                title="후보 결정",
                body=None,
                state=EventState.CANDIDATE,
                priority=EventPriority.DECISION,
                source_utterance_id=candidate_utterance.id,
            )
        )
        repository.save(
            MeetingEvent.create(
                session_id=session_id,
                event_type=EventType.DECISION,
                title="확정 결정",
                body=None,
                state=EventState.CONFIRMED,
                priority=EventPriority.DECISION,
                source_utterance_id=confirmed_utterance.id,
            )
        )

        response = client.post(f"/api/v1/reports/{session_id}/markdown")

        assert response.status_code == 200
        content = response.json()["content"]
        assert "확정 결정" in content
        assert "후보 결정" not in content


def _create_session(client) -> str:
    create_response = client.post(
        "/api/v1/sessions",
        json={
            "title": SESSION_TITLE,
            "mode": "meeting",
            "source": "system_audio",
        },
    )
    return create_response.json()["id"]


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
                    priority=EventPriority.QUESTION,
                    source_utterance_id="utt-1",
                ),
            )
        ]
