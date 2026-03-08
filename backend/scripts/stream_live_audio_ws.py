from __future__ import annotations

import argparse
import asyncio
from contextlib import suppress
import json
import sys
import warnings
from pathlib import Path
from urllib import request

import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError, ConnectionClosedOK


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.audio.io.live_audio_capture import (  # noqa: E402
    LiveAudioCaptureConfig,
    create_live_audio_capture,
    list_microphone_devices,
    resolve_live_capture_device_label,
    list_system_audio_devices,
)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stream live audio to websocket server.")
    parser.add_argument("--source", choices=["mic", "system_audio"], required=True)
    parser.add_argument("--title", default="live-audio-test")
    parser.add_argument("--session-id")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--device-name")
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--channels", type=int, default=1)
    parser.add_argument("--chunk-ms", type=int, default=250)
    parser.add_argument("--max-chunks", type=int, default=0, help="0 means unlimited")
    parser.add_argument("--output-mode", choices=["text", "json"], default="text")
    parser.add_argument("--list-devices", action="store_true")
    return parser


def create_session(base_url: str, title: str, source: str) -> str:
    payload = json.dumps(
        {
            "title": title,
            "mode": "meeting",
            "source": source,
        }
    ).encode("utf-8")
    req = request.Request(
        url=f"{base_url.rstrip('/')}/api/v1/sessions",
        data=payload,
        headers={"Content-Type": "application/json"},
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
) -> None:
    ws_url = base_url.rstrip("/").replace("http://", "ws://").replace("https://", "wss://")
    ws_url = f"{ws_url}/api/v1/ws/audio/{session_id}?input_source={input_source}"

    async with websockets.connect(ws_url, max_size=None) as websocket:
        sender = asyncio.create_task(
            _send_audio_chunks(
                websocket=websocket,
                capture=capture,
                max_chunks=max_chunks,
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
            sender.cancel()
            with suppress(asyncio.CancelledError, ConnectionClosedOK, ConnectionClosedError, ConnectionClosed):
                await sender


async def _send_audio_chunks(*, websocket, capture, max_chunks: int) -> None:
    for index, chunk in enumerate(capture.iter_chunks(), start=1):
        await websocket.send(chunk)
        if max_chunks > 0 and index >= max_chunks:
            with suppress(ConnectionClosedOK, ConnectionClosedError, ConnectionClosed):
                await websocket.close()
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
    parser = build_parser()
    args = parser.parse_args()

    if args.list_devices:
        print_devices(args.source)
        return

    session_id = args.session_id or create_session(args.base_url, args.title, args.source)
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
    try:
        await stream_audio(
            args.base_url,
            session_id,
            capture,
            args.max_chunks,
            args.output_mode,
            args.source,
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

