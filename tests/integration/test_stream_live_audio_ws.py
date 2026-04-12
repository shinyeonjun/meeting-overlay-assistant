"""통합 흐름에서 test stream live audio ws 동작을 검증한다."""
from __future__ import annotations

import server.scripts.audio.stream_live_audio_ws as stream_module
from server.scripts.audio.stream_live_audio_ws import LocalChunkPreprocessor, should_emit_payload


class TestStreamLiveAudioWs:
    """StreamLiveAudioWs 동작을 검증한다."""
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

    def test_capture_info_텍스트_출력은_지연한다(self, monkeypatch):
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

    def test_무음_chunk의_rms는_0이다(self):
        chunk = (0).to_bytes(2, byteorder="little", signed=True) * 4

        assert LocalChunkPreprocessor._measure_rms_ratio(chunk) == 0.0

    def test_비무음_chunk의_rms는_양수다(self):
        sample = (1000).to_bytes(2, byteorder="little", signed=True)
        chunk = sample * 4

        assert LocalChunkPreprocessor._measure_rms_ratio(chunk) > 0.0
