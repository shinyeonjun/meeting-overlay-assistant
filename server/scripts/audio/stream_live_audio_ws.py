from __future__ import annotations

import argparse
import asyncio
from contextlib import suppress
import json
import sys
import warnings
from pathlib import Path
from urllib.parse import quote
from urllib import request
import wave

import numpy as np
import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError, ConnectionClosedOK


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.app.services.audio.io.live_audio_capture import (  # noqa: E402
    LiveAudioCaptureConfig,
    create_live_audio_capture,
    list_microphone_devices,
    resolve_live_capture_device_label,
    list_system_audio_devices,
)
from server.app.services.audio.io.session_recording import (  # noqa: E402
    build_session_recording_path,
)


def configure_console_encoding() -> None:
    """직접 실행되는 CLI 경로에서만 콘솔 인코딩을 UTF-8로 맞춘다."""

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stream live audio to websocket server.")
    parser.add_argument("--source", choices=["mic", "system_audio"], required=True)
    parser.add_argument("--title", default="live-audio-test")
    parser.add_argument("--session-id")
    parser.add_argument("--base-url", default="http://127.0.0.1:8011")
    parser.add_argument("--device-name")
    parser.add_argument("--access-token")
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--channels", type=int, default=1)
    parser.add_argument("--chunk-ms", type=int, default=250)
    parser.add_argument("--max-chunks", type=int, default=0, help="0 means unlimited")
    parser.add_argument("--silence-gate-enabled", action="store_true")
    parser.add_argument("--silence-gate-min-rms", type=float, default=0.0)
    parser.add_argument("--silence-gate-hold-chunks", type=int, default=0)
    parser.add_argument("--output-mode", choices=["text", "json"], default="text")
    parser.add_argument("--list-devices", action="store_true")
    return parser


class LocalChunkPreprocessor:
    def __init__(
        self,
        *,
        silence_gate_enabled: bool,
        silence_gate_min_rms: float,
        silence_gate_hold_chunks: int,
    ) -> None:
        self._silence_gate_enabled = silence_gate_enabled
        self._silence_gate_min_rms = max(float(silence_gate_min_rms), 0.0)
        self._silence_gate_hold_chunks = max(int(silence_gate_hold_chunks), 0)
        self._remaining_hold_chunks = 0

    def should_send(self, chunk: bytes) -> bool:
        if not self._silence_gate_enabled:
            return True

        rms_ratio = self._measure_rms_ratio(chunk)
        if rms_ratio >= self._silence_gate_min_rms:
            self._remaining_hold_chunks = self._silence_gate_hold_chunks
            return True

        if self._remaining_hold_chunks > 0:
            self._remaining_hold_chunks -= 1
            return True

        return False

    @staticmethod
    def _measure_rms_ratio(chunk: bytes) -> float:
        if not chunk:
            return 0.0
        samples = np.frombuffer(chunk, dtype="<i2")
        if samples.size == 0:
            return 0.0
        squared = np.square(samples.astype(np.float64))
        rms = float(np.sqrt(np.mean(squared)))
        return rms / 32768.0


def create_session(base_url: str, title: str, source: str, access_token: str | None = None) -> str:
    payload = json.dumps(
        {
            "title": title,
            "mode": "meeting",
            "source": source,
        }
    ).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    req = request.Request(
        url=f"{base_url.rstrip('/')}/api/v1/sessions",
        data=payload,
        headers=headers,
        method="POST",
    )
    with request.urlopen(req, timeout=20) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body["id"]


def write_stdout_line(line: str) -> bool:
    try:
        sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()
        return True
    except OSError:
        return False


def emit_output(payload: dict, output_mode: str) -> bool:
    if output_mode == "json":
        return write_stdout_line(json.dumps(payload, ensure_ascii=False))

    if payload["type"] == "session":
        return write_stdout_line(f"session_id={payload['session_id']}")
    if payload["type"] == "capture_info":
        return write_stdout_line(
            f"capture_source={payload['source']} capture_device={payload['device_name']}"
        )

    message = payload["payload"]
    if not write_stdout_line(
        f"[chunk {payload['chunk_index']}] utterances={len(message['utterances'])} events={len(message['events'])}",
    ):
        return False
    for utterance in message["utterances"]:
        if not write_stdout_line(
            f"  - utterance: {utterance['text']} (confidence={utterance['confidence']})"
        ):
            return False
    for event in message["events"]:
        if not write_stdout_line(f"  - event: {event['type']} | {event['title']}"):
            return False
    return True


def should_emit_payload(payload: dict) -> bool:
    utterances = payload.get("utterances") or []
    events = payload.get("events") or []
    error = payload.get("error")
    return bool(utterances or events or error)


async def stream_audio(
    base_url: str,
    session_id: str,
    capture,
    max_chunks: int,
    output_mode: str,
    input_source: str,
    recording_path: Path,
    sample_rate: int,
    channels: int,
    preprocessor: LocalChunkPreprocessor,
    access_token: str | None,
) -> None:
    ws_url = base_url.rstrip("/").replace("http://", "ws://").replace("https://", "wss://")
    ws_url = f"{ws_url}/api/v1/ws/audio/{session_id}?input_source={input_source}"
    if access_token:
        ws_url = f"{ws_url}&token={quote(access_token, safe='')}"
    stop_event = asyncio.Event()

    recording_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(recording_path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        async with websockets.connect(ws_url, max_size=None) as websocket:
            stop_watcher = asyncio.create_task(_watch_stop_signal(stop_event))
            sender = asyncio.create_task(
                _send_audio_chunks(
                    websocket=websocket,
                    capture=capture,
                    max_chunks=max_chunks,
                    wav_file=wav_file,
                    stop_event=stop_event,
                    preprocessor=preprocessor,
                )
            )
            payload_index = 0
            try:
                while True:
                    payload = json.loads(await websocket.recv())
                    if not should_emit_payload(payload):
                        continue
                    payload_index += 1
                    if not emit_output(
                        {"type": "payload", "chunk_index": payload_index, "payload": payload},
                        output_mode,
                    ):
                        break
            finally:
                stop_event.set()
                stop_watcher.cancel()
                sender.cancel()
                with suppress(asyncio.CancelledError, ConnectionClosedOK, ConnectionClosedError, ConnectionClosed):
                    await stop_watcher
                with suppress(asyncio.CancelledError, ConnectionClosedOK, ConnectionClosedError, ConnectionClosed):
                    await sender
                with suppress(ConnectionClosedOK, ConnectionClosedError, ConnectionClosed):
                    await websocket.close()
    if recording_path.exists() and recording_path.stat().st_size <= 44:
        recording_path.unlink(missing_ok=True)


async def _send_audio_chunks(
    *,
    websocket,
    capture,
    max_chunks: int,
    wav_file,
    stop_event: asyncio.Event,
    preprocessor: LocalChunkPreprocessor,
) -> None:
    for index, chunk in enumerate(capture.iter_chunks(), start=1):
        if stop_event.is_set():
            with suppress(ConnectionClosedOK, ConnectionClosedError, ConnectionClosed):
                await websocket.close()
            return
        wav_file.writeframes(chunk)
        if not preprocessor.should_send(chunk):
            continue
        await websocket.send(chunk)
        if max_chunks > 0 and index >= max_chunks:
            with suppress(ConnectionClosedOK, ConnectionClosedError, ConnectionClosed):
                await websocket.close()
            return


async def _watch_stop_signal(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        line = await asyncio.to_thread(sys.stdin.readline)
        if not line:
            await asyncio.sleep(0.05)
            continue
        if line.strip().casefold() == "stop":
            stop_event.set()
            return


def print_devices(source: str) -> None:
    devices = list_microphone_devices() if source == "mic" else list_system_audio_devices()
    for device in devices:
        print(device)


def close_capture(capture) -> None:
    close = getattr(capture, "close", None)
    if callable(close):
        close()


async def main() -> None:
    configure_console_encoding()
    parser = build_parser()
    args = parser.parse_args()

    if args.list_devices:
        print_devices(args.source)
        return

    session_id = args.session_id or create_session(
        args.base_url,
        args.title,
        args.source,
        args.access_token,
    )
    if not emit_output({"type": "session", "session_id": session_id}, args.output_mode):
        return

    capture_config = LiveAudioCaptureConfig(
        source=args.source,
        sample_rate_hz=args.sample_rate,
        channels=args.channels,
        chunk_duration_ms=args.chunk_ms,
        device_name=args.device_name,
    )
    capture = create_live_audio_capture(capture_config)
    preprocessor = LocalChunkPreprocessor(
        silence_gate_enabled=args.silence_gate_enabled,
        silence_gate_min_rms=args.silence_gate_min_rms,
        silence_gate_hold_chunks=args.silence_gate_hold_chunks,
    )
    selected_device_name = resolve_live_capture_device_label(capture_config)
    recording_path = build_session_recording_path(session_id, args.source)
    if not emit_output(
        {
            "type": "capture_info",
            "source": args.source,
            "device_name": selected_device_name,
        },
        args.output_mode,
    ):
        close_capture(capture)
        return
    try:
        await stream_audio(
            args.base_url,
            session_id,
            capture,
            args.max_chunks,
            args.output_mode,
            args.source,
            recording_path,
            args.sample_rate,
            args.channels,
            preprocessor,
            args.access_token,
        )
    except (ConnectionClosedOK, ConnectionClosedError, ConnectionClosed, asyncio.CancelledError, BrokenPipeError):
        return
    finally:
        close_capture(capture)


if __name__ == "__main__":
    warnings.filterwarnings(
        "ignore",
        message="data discontinuity in recording",
        category=UserWarning,
    )
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


