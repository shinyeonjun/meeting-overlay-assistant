"""공통 영역의 test shared api contracts 동작을 검증한다."""
from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
API_CONTRACTS_DIR = PROJECT_ROOT / "shared" / "contracts" / "api"


def _load_schema(name: str) -> dict[str, object]:
    path = API_CONTRACTS_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


class TestSharedApiContracts:
    """shared/contracts/api 아래 핵심 schema smoke test."""

    def test_session_schema_contains_current_core_fields(self):
        schema = _load_schema("session.schema.json")
        create_request = schema["properties"]["create_request"]
        link_request = schema["properties"]["participant_contact_link_request"]
        response = schema["properties"]["response"]

        assert create_request["$ref"] == "#/$defs/sessionCreateRequest"
        assert link_request["$ref"] == "#/$defs/sessionParticipantContactLinkRequest"
        assert response["$ref"] == "#/$defs/sessionResponse"

        create_fields = schema["$defs"]["sessionCreateRequest"]["properties"]
        response_fields = schema["$defs"]["sessionResponse"]["properties"]

        assert {
            "title",
            "mode",
            "primary_input_source",
            "account_id",
            "contact_id",
            "context_thread_id",
            "participants",
        } <= set(create_fields)
        assert {
            "id",
            "title",
            "mode",
            "primary_input_source",
            "status",
            "participants",
            "participant_summary",
        } <= set(response_fields)
        summary_fields = schema["$defs"]["sessionParticipantSummaryResponse"]["properties"]
        assert {
            "total_count",
            "linked_count",
            "unmatched_count",
            "ambiguous_count",
            "unresolved_count",
        } <= set(summary_fields)

    def test_auth_schema_contains_current_core_fields(self):
        schema = _load_schema("auth.schema.json")
        config_response = schema["properties"]["auth_config_response"]
        session_response = schema["properties"]["auth_session_response"]

        assert config_response["$ref"] == "#/$defs/authConfigResponse"
        assert session_response["$ref"] == "#/$defs/authSessionResponse"

        config_fields = schema["$defs"]["authConfigResponse"]["properties"]
        user_fields = schema["$defs"]["authUserResponse"]["properties"]
        session_fields = schema["$defs"]["authSessionResponse"]["properties"]

        assert {"enabled", "bootstrap_required", "user_count"} <= set(config_fields)
        assert {"id", "login_id", "display_name", "workspace_role", "status"} <= set(user_fields)
        assert {"access_token", "token_type", "expires_at", "user"} <= set(session_fields)

    def test_existing_shared_api_schemas_are_valid_json(self):
        schema_names = [
            "auth.schema.json",
            "context.schema.json",
            "events.schema.json",
            "history.schema.json",
            "runtime.schema.json",
            "report.schema.json",
            "session.schema.json",
            "session-overview.schema.json",
            "final-report-status.schema.json",
        ]

        for name in schema_names:
            schema = _load_schema(name)
            assert "$schema" in schema
            assert "$id" in schema
            assert "title" in schema

    def test_report_schema_contains_share_contracts(self):
        schema = _load_schema("report.schema.json")
        defs = schema["$defs"]

        assert {"reportItem", "latestReport", "finalReportStatus"} <= set(defs)
        assert {"reportShareItem", "reportShareInboxItem"} <= set(defs)

    def test_events_schema_contains_board_and_transition_contracts(self):
        schema = _load_schema("events.schema.json")
        defs = schema["$defs"]

        assert {"eventItem", "eventListResponse"} <= set(defs)
        assert {"eventUpdateRequest", "eventTransitionRequest"} <= set(defs)
        assert {"bulkEventTransitionRequest", "bulkEventTransitionResponse"} <= set(defs)

    def test_context_schema_contains_catalog_contracts(self):
        schema = _load_schema("context.schema.json")
        defs = schema["$defs"]

        assert {"accountResponse", "contactResponse", "contextThreadResponse"} <= set(defs)

    def test_history_schema_contains_timeline_and_carry_over_contracts(self):
        schema = _load_schema("history.schema.json")
        defs = schema["$defs"]

        assert {"historyTimelineSessionItem", "historyTimelineReportItem"} <= set(defs)
        assert {
            "historyCarryOverItem",
            "historyCarryOverResponse",
            "historyRetrievalBriefItem",
            "historyRetrievalBriefResponse",
            "historyTimelineResponse",
        } <= set(defs)

    def test_runtime_schema_contains_readiness_and_monitor_contracts(self):
        schema = _load_schema("runtime.schema.json")
        defs = schema["$defs"]

        assert {"runtimeReadinessResponse", "runtimeMonitorResponse"} <= set(defs)
        assert {
            "preloadedSourceItem",
            "runtimeMonitorAudioPipelineResponse",
            "runtimeMonitorLiveStreamResponse",
        } <= set(defs)
        live_stream_fields = defs["runtimeMonitorLiveStreamResponse"]["properties"]
        assert {
            "draining_stream_count",
            "coalesced_chunk_count",
        } <= set(live_stream_fields)
