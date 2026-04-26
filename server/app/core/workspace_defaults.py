"""기본 워크스페이스 상수를 정의한다."""

from server.app.core.identifiers import legacy_text_to_uuid_str


DEFAULT_WORKSPACE_ID = legacy_text_to_uuid_str("workspace-default")
DEFAULT_WORKSPACE_SLUG = "default"
DEFAULT_WORKSPACE_NAME = "기본 워크스페이스"
DEFAULT_WORKSPACE_STATUS = "active"
