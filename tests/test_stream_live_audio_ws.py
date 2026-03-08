"""live audio 스트림 출력 정책 테스트"""

import backend.scripts.stream_live_audio_ws as stream_module
from backend.scripts.stream_live_audio_ws import should_emit_payload


class TestStreamLiveAudioWs:
    def test_utterances_events_error가_모두_비어있으면_출력하지_않는다(self):
        assert should_emit_payload(
            {
                "session_id": "session-test",
                "utterances": [],
                "events": [],
                "error": None,
            }
        ) is False

    def test_발화가_있으면_출력한다(self):
        assert should_emit_payload(
            {
                "session_id": "session-test",
                "utterances": [{"text": "안녕하세요"}],
                "events": [],
                "error": None,
            }
        ) is True

    def test_에러가_있으면_출력한다(self):
        assert should_emit_payload(
            {
                "session_id": "session-test",
                "utterances": [],
                "events": [],
                "error": "boom",
            }
        ) is True

    def test_capture_info_텍스트_출력을_지원한다(self, monkeypatch):
        captured_lines: list[str] = []

        def fake_write_stdout_line(line: str) -> bool:
            captured_lines.append(line)
            return True

        monkeypatch.setattr(stream_module, "write_stdout_line", fake_write_stdout_line)
        ok = stream_module.emit_output(
            {
                "type": "capture_info",
                "source": "mic",
                "device_name": "USB Microphone",
            },
            output_mode="text",
        )

        assert ok is True
        assert captured_lines == ["capture_source=mic capture_device=USB Microphone"]

