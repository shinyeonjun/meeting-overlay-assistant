"""개발용 텍스트 chunk 전송 스크립트."""

from __future__ import annotations

import asyncio
import sys

import websockets


async def main() -> None:
    """텍스트를 개발용 WebSocket으로 전송한다."""
    if len(sys.argv) < 3:
        print("사용법: python backend/scripts/send_text_chunk.py <session_id> <text>")
        return

    session_id = sys.argv[1]
    text = " ".join(sys.argv[2:])
    uri = f"ws://127.0.0.1:8000/api/v1/ws/dev-text/{session_id}"

    async with websockets.connect(uri) as websocket:
        await websocket.send(text)
        response = await websocket.recv()
        print(response)


if __name__ == "__main__":
    asyncio.run(main())
