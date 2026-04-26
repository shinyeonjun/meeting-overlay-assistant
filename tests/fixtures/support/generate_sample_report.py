"""음성 입력 파일로 샘플 회의록을 생성하는 지원 스크립트."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fastapi.testclient import TestClient

from server.app.main import app


def build_parser() -> argparse.ArgumentParser:
    """CLI 인자를 정의한다."""
    parser = argparse.ArgumentParser(
        description="샘플 회의 음성 파일로 Markdown/PDF 회의록을 생성합니다."
    )
    parser.add_argument("--audio-path", required=True, help="입력 WAV 파일 경로")
    parser.add_argument(
        "--title",
        default="음성 회의록 검증",
        help="생성할 세션 제목",
    )
    return parser


def main() -> None:
    """샘플 음성 파일로 회의록을 생성한다."""
    parser = build_parser()
    args = parser.parse_args()

    audio_path = Path(args.audio_path).resolve()
    if not audio_path.exists():
        raise FileNotFoundError(f"오디오 파일을 찾을 수 없습니다: {audio_path}")

    with TestClient(app) as client:
        create_response = client.post(
            "/api/v1/sessions",
            json={
                "title": args.title,
                "mode": "meeting",
                "source": "system_audio",
            },
        )
        create_response.raise_for_status()
        session_id = create_response.json()["id"]

        end_response = client.post(f"/api/v1/sessions/{session_id}/end")
        end_response.raise_for_status()

        markdown_response = client.post(
            f"/api/v1/reports/{session_id}/markdown",
            params={"audio_path": str(audio_path)},
        )
        markdown_response.raise_for_status()

        pdf_response = client.post(
            f"/api/v1/reports/{session_id}/pdf",
            params={"audio_path": str(audio_path)},
        )
        pdf_response.raise_for_status()

        latest_response = client.get(f"/api/v1/reports/{session_id}/latest")
        latest_response.raise_for_status()

        result = {
            "session_id": session_id,
            "audio_path": str(audio_path),
            "markdown": markdown_response.json(),
            "pdf": pdf_response.json(),
            "latest": latest_response.json(),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
