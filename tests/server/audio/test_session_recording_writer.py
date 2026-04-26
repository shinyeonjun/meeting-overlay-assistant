"""세션 녹음 writer와 runtime helper 테스트."""

from __future__ import annotations

import asyncio
import wave
from pathlib import Path

from server.app.api.http.routes.websocket_streaming_helpers.session_runtime import (
    build_recording_writer,
    close_stream_context,
)
from server.app.services.audio.io.session_recording_writer import SessionRecordingWriter


class _FakeLiveStreamService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def close_input(self, context_id: str) -> None:
        self.calls.append(("close_input", context_id))

    async def close_stream(self, context_id: str) -> None:
        self.calls.append(("close_stream", context_id))


class _FakeWriter:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_session_recording_writer가_wav파일을_정상적으로_쓴다(tmp_path: Path) -> None:
    output_path = tmp_path / "recording.wav"
    writer = SessionRecordingWriter(
        output_path=output_path,
        sample_rate_hz=16000,
        sample_width_bytes=2,
        channels=1,
    )

    writer.append_chunk(b"\x00\x00\x01\x00\x02\x00\x03\x00")
    writer.append_chunk(b"\x04\x00\x05\x00")
    writer.close()

    with wave.open(str(output_path), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == 16000
        assert wav_file.readframes(wav_file.getnframes()) == b"\x00\x00\x01\x00\x02\x00\x03\x00\x04\x00\x05\x00"


def test_session_recording_writer가_빈_chunk는_무시한다(tmp_path: Path) -> None:
    output_path = tmp_path / "empty.wav"
    writer = SessionRecordingWriter(
        output_path=output_path,
        sample_rate_hz=16000,
        sample_width_bytes=2,
        channels=1,
    )

    writer.append_chunk(b"")
    writer.close()

    assert output_path.exists() is False


def test_build_recording_writer는_audio일때만_writer를_만든다() -> None:
    audio_writer = build_recording_writer(
        session_id="session-1",
        input_source="mic",
        stream_kind="audio",
    )
    caption_writer = build_recording_writer(
        session_id="session-1",
        input_source="mic",
        stream_kind="caption",
    )

    assert isinstance(audio_writer, SessionRecordingWriter)
    assert caption_writer is None
    assert str(audio_writer.output_path).endswith("session-1\\mic.wav")


def test_close_stream_context가_writer까지_정리한다() -> None:
    live_stream_service = _FakeLiveStreamService()
    writer = _FakeWriter()

    asyncio.run(
        close_stream_context(
            live_stream_service=live_stream_service,
            context_id="context-1",
            recording_writer=writer,
        )
    )

    assert live_stream_service.calls == [
        ("close_input", "context-1"),
        ("close_stream", "context-1"),
    ]
    assert writer.closed is True
