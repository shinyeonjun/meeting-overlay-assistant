"""실제 WAV 파일을 오디오 WebSocket으로 전송하는 e2e 스크립트."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from urllib import request

import websockets

from backend.app.services.audio.io.wav_chunk_reader import read_pcm_wave_file, split_pcm_bytes


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WAV 파일을 오디오 WebSocket으로 스트리밍합니다.")
    parser.add_argument("--wav", required=True, help="16kHz/mono/16-bit PCM WAV 파일 경로")
    parser.add_argument("--title", default="오디오 E2E 테스트", help="생성할 세션 제목")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API 서버 기본 URL")
    parser.add_argument("--chunk-ms", type=int, default=250, help="전송 청크 길이(ms)")
    parser.add_argument("--delay-ms", type=int, default=150, help="청크 간 대기 시간(ms)")
    return parser


def _create_session(base_url: str, title: str) -> str:
    payload = json.dumps(
        {
            "title": title,
            "mode": "meeting",
            "source": "system_audio",
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


def _get_overview(base_url: str, session_id: str) -> dict:
    with request.urlopen(
        f"{base_url.rstrip('/')}/api/v1/sessions/{session_id}/overview",
        timeout=20,
    ) as response:
        return json.loads(response.read().decode("utf-8"))


def _create_markdown_report(base_url: str, session_id: str) -> dict:
    req = request.Request(
        url=f"{base_url.rstrip('/')}/api/v1/reports/{session_id}/markdown",
        data=b"",
        method="POST",
    )
    with request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


async def _stream_audio(
    *,
    base_url: str,
    session_id: str,
    chunks: list[bytes],
    delay_ms: int,
) -> None:
    ws_url = base_url.rstrip("/").replace("http://", "ws://").replace("https://", "wss://")
    ws_url = f"{ws_url}/api/v1/ws/audio/{session_id}"

    async with websockets.connect(ws_url, max_size=None) as websocket:
        for index, chunk in enumerate(chunks, start=1):
            await websocket.send(chunk)
            payload = json.loads(await websocket.recv())
            print(f"[chunk {index}] utterances={len(payload['utterances'])} events={len(payload['events'])}")
            for utterance in payload["utterances"]:
                print(f"  - utterance: {utterance['text']} (confidence={utterance['confidence']})")
            for event in payload["events"]:
                print(f"  - event: {event['type']} | {event['title']}")
            await asyncio.sleep(delay_ms / 1000)


async def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    wave_audio = read_pcm_wave_file(
        Path(args.wav),
        expected_sample_rate_hz=16000,
        expected_sample_width_bytes=2,
        expected_channels=1,
    )
    chunks = split_pcm_bytes(
        wave_audio.raw_bytes,
        sample_rate_hz=wave_audio.sample_rate_hz,
        sample_width_bytes=wave_audio.sample_width_bytes,
        channels=wave_audio.channels,
        chunk_duration_ms=args.chunk_ms,
    )

    session_id = _create_session(args.base_url, args.title)
    print(f"session_id={session_id}")
    await _stream_audio(
        base_url=args.base_url,
        session_id=session_id,
        chunks=chunks,
        delay_ms=args.delay_ms,
    )

    overview = _get_overview(args.base_url, session_id)
    report = _create_markdown_report(args.base_url, session_id)
    print("overview=", json.dumps(overview, ensure_ascii=False, indent=2))
    print("report=", json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

