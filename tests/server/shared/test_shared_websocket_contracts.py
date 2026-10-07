"""shared websocket 계약이 현재 live payload 의미를 반영하는지 검증한다."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
WEBSOCKET_CONTRACTS_DIR = PROJECT_ROOT / "shared" / "contracts" / "websocket"


def _load_schema(name: str) -> dict[str, object]:
    path = WEBSOCKET_CONTRACTS_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


class TestSharedWebsocketContracts:
    """shared/contracts/websocket 아래 계약 스모크 테스트."""

    def test_live_caption_schema_contains_archive_final_contract(self):
        schema = _load_schema("live-caption.schema.json")
        utterance = schema["$defs"]["utterance"]

        assert {
            "id",
            "seq_num",
            "segment_id",
            "text",
            "confidence",
            "start_ms",
            "end_ms",
            "is_partial",
            "kind",
            "revision",
            "input_source",
            "stability",
        } <= set(utterance["properties"])
        assert utterance["properties"]["kind"]["enum"] == [
            "preview",
            "live_final",
            "archive_final",
            "late_archive_final",
        ]
        assert utterance["properties"]["stability"]["enum"] == ["low", "medium", "final", None]

    def test_live_caption_schema_contains_current_event_contract(self):
        schema = _load_schema("live-caption.schema.json")
        event = schema["$defs"]["event"]

        assert {"id", "type", "title", "state", "source_utterance_id"} <= set(event["properties"])
        assert event["properties"]["type"]["enum"] == [
            "topic",
            "question",
            "decision",
            "action_item",
            "risk",
        ]
        assert event["properties"]["state"]["enum"] == [
            "active",
            "open",
            "answered",
            "confirmed",
            "updated",
            "resolved",
            "closed",
        ]
