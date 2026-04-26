"""식별자 helper 테스트."""

from uuid import UUID

from server.app.core.identifiers import generate_uuid_str, legacy_text_to_uuid_str
from server.app.core.workspace_defaults import DEFAULT_WORKSPACE_ID


class TestIdentifierHelpers:
    """UUID 식별자 helper를 검증한다."""

    def test_generate_uuid_str가_uuid_문자열을_반환한다(self):
        generated = generate_uuid_str()

        assert str(UUID(generated)) == generated

    def test_legacy_text_to_uuid_str가_32자리_hex_suffix를_uuid로_바꾼다(self):
        converted = legacy_text_to_uuid_str("session-55555555555555555555555555555555")

        assert converted == "55555555-5555-5555-5555-555555555555"

    def test_legacy_text_to_uuid_str가_default_workspace와_같은_정규화를_쓴다(self):
        assert legacy_text_to_uuid_str("workspace-default") == DEFAULT_WORKSPACE_ID
