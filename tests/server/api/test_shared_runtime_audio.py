"""공통 영역의 test shared runtime audio 동작을 검증한다."""
from __future__ import annotations

from dataclasses import replace

from server.app.api.http.wiring.shared_service_providers import runtime as runtime_module


class TestSharedRuntimeAudio:
    """노트 후처리 helper가 별도 beam 설정을 적용하는지 검증한다."""

    def test_create_postprocessing_speech_to_text_service는_note_beam_override를_적용한다(
        self,
        monkeypatch,
    ):
        captured: dict[str, object] = {}

        monkeypatch.setattr(
            runtime_module,
            "settings",
            replace(
                runtime_module.settings,
                note_transcript_stt_model_id="test/note-model",
                note_transcript_stt_model_path="server/models/stt/test-note-model",
                note_transcript_stt_beam_size=7,
            ),
        )

        def _fake_create_service_from_options(options):
            captured["backend_name"] = options.backend_name
            captured["model_id"] = options.model_id
            captured["model_path"] = options.model_path
            captured["beam_size"] = options.beam_size
            return object()

        monkeypatch.setattr(
            runtime_module,
            "create_speech_to_text_service_from_options",
            _fake_create_service_from_options,
        )

        runtime_module.create_postprocessing_speech_to_text_service("file")

        assert captured["backend_name"] == "faster_whisper"
        assert captured["model_id"] == "test/note-model"
        assert captured["model_path"] == "server/models/stt/test-note-model"
        assert captured["beam_size"] == 7
