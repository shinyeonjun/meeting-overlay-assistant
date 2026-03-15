"""개발용 텍스트 chunk 전송 스크립트."""

from __future__ import annotations

import argparse
import asyncio

import websockets


def build_parser() -> argparse.ArgumentParser:
    """CLI 인자를 정의한다."""
    parser = argparse.ArgumentParser(description="텍스트 WebSocket으로 chunk를 전송합니다.")
    parser.add_argument("session_id", help="대상 세션 ID")
    parser.add_argument("text", nargs="+", help="전송할 텍스트")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8011",
        help="API 서버 기본 URL",
    )
    return parser


async def main() -> None:
    """텍스트를 개발용 WebSocket으로 전송한다."""
    parser = build_parser()
    args = parser.parse_args()

    text = " ".join(args.text)
    ws_base_url = args.base_url.rstrip("/").replace("http://", "ws://").replace("https://", "wss://")
    uri = f"{ws_base_url}/api/v1/ws/text/{args.session_id}"

    async with websockets.connect(uri) as websocket:
        await websocket.send(text)
        response = await websocket.recv()
        print(response)


if __name__ == "__main__":
    asyncio.run(main())
