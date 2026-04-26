"""세션 임시 녹음 파일 유틸리티 테스트."""

from __future__ import annotations

import os

from server.app.services.audio.io.session_recording import (
    build_session_recording_artifact,
    build_session_recording_path,
    find_session_recording_artifact,
    find_session_recording_path,
    get_session_recordings_dir,
)


class TestSessionRecording:
    """세션 임시 녹음 파일 경로 규칙을 검증한다."""

    def test_세션_녹음_경로를_세션과_입력소스_기준으로_만든다(self, tmp_path):
        artifact = build_session_recording_artifact(
            "session-test",
            "system_audio",
            root_dir=tmp_path,
        )
        recording_path = build_session_recording_path(
            "session-test",
            "system_audio",
            root_dir=tmp_path,
        )

        assert artifact.artifact_id == "recordings/session-test/system_audio.wav"
        assert recording_path == get_session_recordings_dir(tmp_path) / "session-test" / "system_audio.wav"

    def test_세션_녹음_파일이_여러개면_가장_최근_파일을_찾는다(self, tmp_path):
        recordings_dir = get_session_recordings_dir(tmp_path) / "session-test"
        recordings_dir.mkdir(parents=True, exist_ok=True)
        older = recordings_dir / "mic.wav"
        newer = recordings_dir / "system_audio.wav"
        older.write_bytes(b"older")
        newer.write_bytes(b"newer")
        os.utime(older, (1, 1))
        os.utime(newer, (2, 2))

        artifact = find_session_recording_artifact("session-test", root_dir=tmp_path)
        result = find_session_recording_path("session-test", root_dir=tmp_path)

        assert artifact is not None
        assert artifact.artifact_id == "recordings/session-test/system_audio.wav"
        assert result == newer
