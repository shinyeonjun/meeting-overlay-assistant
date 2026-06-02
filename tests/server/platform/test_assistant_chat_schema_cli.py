from server.scripts.admin import manage_postgresql


def test_ensure_assistant_chat_schema_parser_defaults_to_dry_run():
    parser = manage_postgresql.build_parser()

    args = parser.parse_args(["ensure-assistant-chat-schema"])

    assert args.command == "ensure-assistant-chat-schema"
    assert args.execute is False
    assert args.print_sql is False


def test_ensure_assistant_chat_schema_parser_accepts_execute_and_print_sql():
    parser = manage_postgresql.build_parser()

    args = parser.parse_args(["ensure-assistant-chat-schema", "--execute", "--print-sql"])

    assert args.command == "ensure-assistant-chat-schema"
    assert args.execute is True
    assert args.print_sql is True


def test_build_assistant_chat_schema_sql_uses_runtime_text_identifier_type():
    sql_text = manage_postgresql.build_assistant_chat_schema_sql("TEXT")

    assert "CREATE TABLE IF NOT EXISTS assistant_conversations" in sql_text
    assert "id TEXT PRIMARY KEY" in sql_text
    assert "workspace_id TEXT NOT NULL" in sql_text
    assert "CREATE TABLE IF NOT EXISTS assistant_response_jobs" in sql_text
    assert "idx_assistant_response_jobs_claimable" in sql_text


def test_build_assistant_chat_schema_sql_uses_typed_uuid_identifier_type():
    sql_text = manage_postgresql.build_assistant_chat_schema_sql("UUID")

    assert "id UUID PRIMARY KEY" in sql_text
    assert "workspace_id UUID NOT NULL" in sql_text
    assert "requested_by_user_id UUID" in sql_text
