"""로컬 artifact 저장소 경로 규칙 테스트."""

from __future__ import annotations

import os

import pytest

from server.app.infrastructure.artifacts import LocalArtifact, LocalArtifactStore


class TestLocalArtifactStore:
    def test_녹음_artifact_id와_경로를_만든다(self, tmp_path):
        store = LocalArtifactStore(tmp_path)

        artifact = store.build_recording_artifact(session_id="s1", input_source="mic")

        assert artifact.artifact_id == "recordings/s1/mic.wav"
        assert artifact.file_path == tmp_path / "recordings" / "s1" / "mic.wav"

    def test_리포트_artifact_확장자는_종류를_따른다(self, tmp_path):
        store = LocalArtifactStore(tmp_path)

        markdown = store.build_report_artifact(session_id="s1", report_type="markdown", version=2)
        pdf = store.build_report_artifact(session_id="s1", report_type="pdf", version=1)

        assert markdown.artifact_id == "reports/s1/markdown/v2/report.md"
        assert pdf.artifact_id == "reports/s1/pdf/v1/report.pdf"
        assert pdf.file_path == tmp_path / "reports" / "s1" / "pdf" / "v1" / "report.pdf"

    def test_최신_녹음은_수정시각_기준으로_찾는다(self, tmp_path):
        store = LocalArtifactStore(tmp_path)
        session_dir = store.get_recordings_dir() / "s1"
        session_dir.mkdir(parents=True)
        older = session_dir / "z_old.wav"
        newer = session_dir / "a_new.wav"
        older.write_bytes(b"old")
        newer.write_bytes(b"new")
        os.utime(older, ns=(1_000_000_000, 1_000_000_000))
        os.utime(newer, ns=(2_000_000_000, 2_000_000_000))
        (session_dir / "notes.txt").write_text("ignored", encoding="utf-8")

        artifact = store.find_latest_recording_artifact("s1")

        assert artifact == LocalArtifact(artifact_id="recordings/s1/a_new.wav", file_path=newer)

    def test_녹음이_없으면_None을_반환한다(self, tmp_path):
        assert LocalArtifactStore(tmp_path).find_latest_recording_artifact("missing") is None

    def test_artifact_id가_없으면_fallback_경로를_쓴다(self, tmp_path):
        store = LocalArtifactStore(tmp_path)

        assert store.resolve_path_or_none(None) is None
        assert store.resolve_path_or_none(None, fallback_path="x/report.md") == tmp_path.__class__("x/report.md")
        assert store.resolve_path_or_none("reports/s1/pdf/v1/report.pdf", fallback_path="ignored") == (
            tmp_path / "reports" / "s1" / "pdf" / "v1" / "report.pdf"
        )

    @pytest.mark.parametrize(
        "artifact_id",
        ["../outside.txt", "reports/../../outside.txt", "/etc/passwd", "C:/Windows/win.ini", "", "a//b"],
    )
    def test_루트_밖을_가리키는_id는_거부한다(self, tmp_path, artifact_id):
        with pytest.raises(ValueError):
            LocalArtifactStore(tmp_path).resolve_path(artifact_id)

    def test_경로_구성요소에_구분자가_있으면_거부한다(self, tmp_path):
        store = LocalArtifactStore(tmp_path)

        with pytest.raises(ValueError):
            store.build_recording_artifact(session_id="../s1", input_source="mic")
        with pytest.raises(ValueError):
            store.build_report_artifact(session_id="s1", report_type="markdown", version=0)
