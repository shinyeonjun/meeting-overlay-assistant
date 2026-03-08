"""세션 종료 시 고정밀 리포트 연결 테스트."""

from __future__ import annotations

from pathlib import Path

from backend.app.domain.shared.enums import AudioSource, SessionMode, SessionStatus
from backend.app.infrastructure.persistence.sqlite.database import Database
from backend.app.infrastructure.persistence.sqlite.repositories.session_repository import (
    SQLiteSessionRepository,
)
from backend.app.services.sessions.session_finalization_service import (
    SessionFinalizationService,
)
from backend.app.services.sessions.session_service import SessionService


class _RecordingAwareReportService:
    def __init__(self) -> None:
        self.list_reports_calls: list[str] = []
        self.regenerate_calls: list[tuple[str, Path, Path | None]] = []

    def list_reports(self, session_id: str) -> list:
        self.list_reports_calls.append(session_id)
        return []

    def regenerate_reports(self, *, session_id: str, output_dir: Path, audio_path: Path | None = None):
        self.regenerate_calls.append((session_id, output_dir, audio_path))
        return None


class TestSessionFinalizationService:
    """세션 종료 시 임시 녹음 파일을 최종 리포트에 연결하는지 검증한다."""

    def test_세션_종료_시_녹음_파일이_있으면_고정밀_리포트_경로를_사용하고_삭제한다(
        self,
        monkeypatch,
        tmp_path,
    ):
        monkeypatch.setattr(
            "backend.app.services.sessions.session_finalization_service.ROOT_DIR",
            tmp_path,
        )
        database = Database(tmp_path / "test.db")
        database.initialize()
        session_repository = SQLiteSessionRepository(database)
        session_service = SessionService(session_repository)
        report_service = _RecordingAwareReportService()
        finalization_service = SessionFinalizationService(session_service, report_service)
        session = session_service.start_session(
            title="테스트 회의",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        recording_path = tmp_path / "session-test.wav"
        recording_path.write_bytes(b"fake wav bytes")
        monkeypatch.setattr(
            "backend.app.services.sessions.session_finalization_service.find_session_recording_path",
            lambda session_id: recording_path if session_id == session.id else None,
        )

        ended_session = finalization_service.finalize_session(session.id)

        assert ended_session.status == SessionStatus.ENDED
        assert report_service.regenerate_calls == [
            (
                session.id,
                tmp_path / "backend" / "data" / "reports",
                recording_path,
            )
        ]
        assert not recording_path.exists()

    def test_세션_종료_시_녹음_파일이_없으면_live_fallback으로_리포트를_생성한다(
        self,
        monkeypatch,
        tmp_path,
    ):
        monkeypatch.setattr(
            "backend.app.services.sessions.session_finalization_service.ROOT_DIR",
            tmp_path,
        )
        database = Database(tmp_path / "test.db")
        database.initialize()
        session_repository = SQLiteSessionRepository(database)
        session_service = SessionService(session_repository)
        report_service = _RecordingAwareReportService()
        finalization_service = SessionFinalizationService(session_service, report_service)
        session = session_service.start_session(
            title="테스트 회의",
            mode=SessionMode.MEETING,
            source=AudioSource.SYSTEM_AUDIO,
        )
        monkeypatch.setattr(
            "backend.app.services.sessions.session_finalization_service.find_session_recording_path",
            lambda session_id: None,
        )

        ended_session = finalization_service.finalize_session(session.id)

        assert ended_session.status == SessionStatus.ENDED
        assert report_service.regenerate_calls == [
            (
                session.id,
                tmp_path / "backend" / "data" / "reports",
                None,
            )
        ]
