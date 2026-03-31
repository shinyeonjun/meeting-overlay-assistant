"""AppConfig 생성값 조립 helper."""

from __future__ import annotations

from server.app.core.config_helpers.app_config_sections import (
    build_ai_values,
    build_audio_values,
    build_base_values,
)


def build_app_config_values() -> dict[str, object]:
    """환경 변수에서 AppConfig 생성 인자를 조립한다."""

    values: dict[str, object] = {}
    values.update(build_base_values())
    values.update(build_audio_values())
    values.update(build_ai_values())
    return values
