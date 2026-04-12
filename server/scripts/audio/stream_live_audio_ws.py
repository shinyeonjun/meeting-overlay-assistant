from __future__ import annotations

import argparse
import asyncio
from contextlib import suppress
import json
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from urllib import request
from urllib.parse import quote
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
    list_system_audio_devices,
    resolve_live_capture_device_label,
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
    parser.add_argument(
        "--prewarm-only",
        action="store_true",
        help="오디오 캡처만 미리 준비하고 stdin 명령으로 세션 연결을 나중에 시작한다.",
    )
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

    def reset(self) -> None:
        self._remaining_hold_chunks = 0

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


def build_ws_url(
    *,
    base_url: str,
    session_id: str,
    input_source: str,
    access_token: str | None,
) -> str:
    ws_url = base_url.rstrip("/").replace("http://", "ws://").replace("https://", "wss://")
    ws_url = f"{ws_url}/api/v1/ws/audio/{session_id}?input_source={input_source}"
    if access_token:
        ws_url = f"{ws_url}&token={quote(access_token, safe='')}"
    return ws_url


@dataclass(slots=True)
class StartStreamCommand:
    session_id: str
    base_url: str
    access_token: str | None


class ActiveStreamSession:
    def __init__(
        self,
        *,
        output_mode: str,
        input_source: str,
        sample_rate: int,
        channels: int,
    ) -> None:
        self._output_mode = output_mode
        self._input_source = input_source
        self._sample_rate = sample_rate
        self._channels = channels
        self._payload_index = 0
        self._session_id: str | None = None
        self._websocket = None
        self._receiver_task: asyncio.Task | None = None
        self._recording_path: Path | None = None
        self._wav_file = None

    @property
    def active(self) -> bool:
        return self._websocket is not None and self._wav_file is not None

    async def activate(self, command: StartStreamCommand) -> None:
        await self.deactivate()

        ws_url = build_ws_url(
            base_url=command.base_url,
            session_id=command.session_id,
            input_source=self._input_source,
            access_token=command.access_token,
        )
        websocket = await websockets.connect(ws_url, max_size=None)
        recording_path = build_session_recording_path(command.session_id, self._input_source)
        recording_path.parent.mkdir(parents=True, exist_ok=True)

        wav_file = wave.open(str(recording_path), "wb")
        wav_file.setnchannels(self._channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(self._sample_rate)

        self._session_id = command.session_id
        self._websocket = websocket
        self._recording_path = recording_path
        self._wav_file = wav_file
        self._payload_index = 0
        self._receiver_task = asyncio.create_task(self._receive_payloads())

    async def deactivate(self) -> None:
        receiver_task = self._receiver_task
        websocket = self._websocket
        wav_file = self._wav_file
        recording_path = self._recording_path

        self._receiver_task = None
        self._websocket = None
        self._wav_file = None
        self._recording_path = None
        self._session_id = None

        if receiver_task:
            receiver_task.cancel()
        if websocket is not None:
            with suppress(ConnectionClosedOK, ConnectionClosedError, ConnectionClosed):
                await websocket.close()
        if receiver_task:
            with suppress(asyncio.CancelledError, ConnectionClosedOK, ConnectionClosedError, ConnectionClosed):
                await receiver_task
        if wav_file is not None:
            wav_file.close()
        if recording_path and recording_path.exists() and recording_path.stat().st_size <= 44:
            recording_path.unlink(missing_ok=True)

    async def send_chunk(
        self,
        *,
        chunk: bytes,
        preprocessor: LocalChunkPreprocessor,
    ) -> None:
        if not self.active:
            return

        self._wav_file.writeframes(chunk)
        if not preprocessor.should_send(chunk):
            return

        try:
            await self._websocket.send(chunk)
        except (ConnectionClosedOK, ConnectionClosedError, ConnectionClosed):
            await self.deactivate()

    async def _receive_payloads(self) -> None:
        assert self._websocket is not None
        try:
            while True:
                payload = json.loads(await self._websocket.recv())
                if not should_emit_payload(payload):
                    continue
                self._payload_index += 1
                if not emit_output(
                    {
                        "type": "payload",
                        "chunk_index": self._payload_index,
                        "payload": payload,
                    },
                    self._output_mode,
                ):
                    return
        except (ConnectionClosedOK, ConnectionClosedError, ConnectionClosed, asyncio.CancelledError):
            return


async def _watch_control_signal(
    *,
    command_queue: asyncio.Queue[StartStreamCommand],
    shutdown_event: asyncio.Event,
) -> None:
    while not shutdown_event.is_set():
        line = await asyncio.to_thread(sys.stdin.readline)
        if not line:
            await asyncio.sleep(0.05)
            continue

        stripped = line.strip()
        if not stripped:
            continue
        if stripped.casefold() == "stop":
            shutdown_event.set()
            return

        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            continue

        if payload.get("type") != "start_stream":
            continue

        session_id = str(payload.get("session_id") or "").strip()
        base_url = str(payload.get("base_url") or "").strip()
        access_token = payload.get("access_token")
        if not session_id or not base_url:
            continue

        await command_queue.put(
            StartStreamCommand(
                session_id=session_id,
                base_url=base_url,
                access_token=access_token,
            )
        )


async def _drain_start_commands(
    *,
    stream_session: ActiveStreamSession,
    command_queue: asyncio.Queue[StartStreamCommand],
    preprocessor: LocalChunkPreprocessor,
) -> None:
    while True:
        try:
            command = command_queue.get_nowait()
        except asyncio.QueueEmpty:
            return
        preprocessor.reset()
        await stream_session.activate(command)


async def stream_audio_loop(
    *,
    capture,
    max_chunks: int,
    preprocessor: LocalChunkPreprocessor,
    stream_session: ActiveStreamSession,
    command_queue: asyncio.Queue[StartStreamCommand],
    shutdown_event: asyncio.Event,
) -> None:
    chunk_iterator = iter(capture.iter_chunks())
    index = 0

    while not shutdown_event.is_set():
        chunk = await asyncio.to_thread(_read_next_chunk, chunk_iterator)
        if chunk is None:
            return

        index += 1
        await _drain_start_commands(
            stream_session=stream_session,
            command_queue=command_queue,
            preprocessor=preprocessor,
        )

        if shutdown_event.is_set():
            return

        await stream_session.send_chunk(
            chunk=chunk,
            preprocessor=preprocessor,
        )

        if max_chunks > 0 and index >= max_chunks:
            shutdown_event.set()
            return


def _read_next_chunk(chunk_iterator):
    try:
        return next(chunk_iterator)
    except StopIteration:
        return None


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

    session_id: str | None = None
    if not args.prewarm_only:
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
    selected_device_name = resolve_live_capture_device_label(capture_config)
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

    preprocessor = LocalChunkPreprocessor(
        silence_gate_enabled=args.silence_gate_enabled,
        silence_gate_min_rms=args.silence_gate_min_rms,
        silence_gate_hold_chunks=args.silence_gate_hold_chunks,
    )
    stream_session = ActiveStreamSession(
        output_mode=args.output_mode,
        input_source=args.source,
        sample_rate=args.sample_rate,
        channels=args.channels,
    )
    command_queue: asyncio.Queue[StartStreamCommand] = asyncio.Queue()
    shutdown_event = asyncio.Event()

    if session_id:
        await stream_session.activate(
            StartStreamCommand(
                session_id=session_id,
                base_url=args.base_url,
                access_token=args.access_token,
            )
        )

    control_task = asyncio.create_task(
        _watch_control_signal(
            command_queue=command_queue,
            shutdown_event=shutdown_event,
        )
    )

    try:
        await stream_audio_loop(
            capture=capture,
            max_chunks=args.max_chunks,
            preprocessor=preprocessor,
            stream_session=stream_session,
            command_queue=command_queue,
            shutdown_event=shutdown_event,
        )
    except (ConnectionClosedOK, ConnectionClosedError, ConnectionClosed, asyncio.CancelledError, BrokenPipeError):
        return
    finally:
        shutdown_event.set()
        control_task.cancel()
        with suppress(asyncio.CancelledError):
            await control_task
        await stream_session.deactivate()
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
