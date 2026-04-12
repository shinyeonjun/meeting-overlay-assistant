"""shared enum catalog와 서버 구현이 같은 값을 바라보는지 검증한다."""

from __future__ import annotations

import json
from pathlib import Path

from server.app.core.workspace_roles import VALID_WORKSPACE_ROLES
from server.app.domain.shared.enums import AudioSource, EventState, EventType, SessionMode, SessionStatus


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENUM_CATALOG_PATH = PROJECT_ROOT / "shared" / "enums" / "catalog.json"


def _load_catalog() -> dict[str, object]:
    return json.loads(ENUM_CATALOG_PATH.read_text(encoding="utf-8"))


class TestSharedEnumCatalog:
    """shared enum catalog가 현재 서버 기준과 어긋나지 않는지 확인한다."""

    def test_server_enum_values_match_shared_catalog(self):
        catalog = _load_catalog()

        assert catalog["session_mode"] == [item.value for item in SessionMode]
        assert catalog["session_status"] == [item.value for item in SessionStatus]
        assert catalog["audio_source"] == [item.value for item in AudioSource]
        assert catalog["workspace_role"] == list(VALID_WORKSPACE_ROLES)
        assert catalog["event_type"] == [item.value for item in EventType]
        assert catalog["event_state"] == [item.value for item in EventState]

    def test_contract_only_values_are_explicit(self):
        catalog = _load_catalog()

        assert catalog["history_scope"] == ["mine", "all"]
        assert catalog["report_format"] == ["markdown", "pdf"]
        assert catalog["final_report_status"] == ["pending", "processing", "completed", "failed"]
        assert catalog["report_share_permission"] == ["view"]
        assert catalog["insight_source"] == ["live_fallback", "high_precision_audio"]
        assert catalog["insight_scope"] == ["live", "report"]
        assert catalog["live_utterance_kind"] == ["preview", "live_final", "archive_final", "late_archive_final"]
        assert catalog["live_utterance_stability"] == ["low", "medium", "final"]
        assert catalog["auth_token_type"] == ["bearer"]

    def test_event_state_by_type_is_subset_of_global_event_states(self):
        catalog = _load_catalog()
        global_states = set(catalog["event_state"])
        per_type = catalog["event_state_by_type"]

        assert set(per_type) == {"question", "decision", "action_item", "risk"}
        for states in per_type.values():
            assert set(states).issubset(global_states)

    def test_all_catalog_values_are_lowercase_snake_case_like_strings(self):
        catalog = _load_catalog()

        for key, values in catalog.items():
            if isinstance(values, list):
                for value in values:
                    assert value == value.lower()
                    assert " " not in value
            elif isinstance(values, dict):
                for nested_key, nested_values in values.items():
                    assert nested_key == nested_key.lower()
                    assert " " not in nested_key
                    for value in nested_values:
                        assert value == value.lower()
                        assert " " not in value
