"""PostgreSQL 보조 CLI의 스키마 선택 계약을 검증한다."""

from server.scripts.admin import manage_postgresql


class TestManagePostgresqlCli:
    """추가된 typed-target 스키마 진입점이 깨지지 않는지 검증한다."""

    def test_apply_schema_parser가_typed_target을_허용한다(self):
        parser = manage_postgresql.build_parser()

        args = parser.parse_args(["apply-schema", "--schema", "typed-target"])

        assert args.command == "apply-schema"
        assert args.schema == "typed-target"

    def test_resolve_schema_path가_typed_target_sql을_반환한다(self):
        schema_path = manage_postgresql.resolve_schema_path("typed-target", None)

        assert schema_path == manage_postgresql.DEFAULT_TYPED_TARGET_SCHEMA_PATH
        assert schema_path.name == "021_runtime_typed_target_schema.sql"

    def test_apply_schema_parser가_typed_migration을_허용한다(self):
        parser = manage_postgresql.build_parser()

        args = parser.parse_args(["apply-schema", "--schema", "typed-migration"])

        assert args.command == "apply-schema"
        assert args.schema == "typed-migration"

    def test_resolve_schema_path가_typed_migration_sql을_반환한다(self):
        schema_path = manage_postgresql.resolve_schema_path("typed-migration", None)

        assert schema_path == manage_postgresql.DEFAULT_TYPED_MIGRATION_SCHEMA_PATH
        assert schema_path.name == "022_runtime_typed_inplace_migration.sql"
