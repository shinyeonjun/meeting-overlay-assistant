"""입력 소스 정책 값 계산 facade."""

from __future__ import annotations

from server.app.core.audio_source_policy_helpers.guard_values import build_guard_values
from server.app.core.audio_source_policy_helpers.policy_context import build_policy_context
from server.app.core.audio_source_policy_helpers.runtime_values import build_runtime_values
from server.app.core.audio_source_policy_helpers.vad_values import build_vad_values
from server.app.core.config import AppConfig


def build_audio_source_policy_kwargs(
    *,
    source: str,
    settings: AppConfig,
    profiles: dict[str, dict[str, object]],
) -> dict[str, object]:
    """입력 소스별 정책 kwargs를 계산한다."""

    is_system_audio, profile_data = build_policy_context(
        source=source,
        settings=settings,
        profiles=profiles,
    )

    return {
        "source": source,
        **build_vad_values(
            profile_data=profile_data,
            settings=settings,
            is_system_audio=is_system_audio,
        ),
        **build_guard_values(
            profile_data=profile_data,
            settings=settings,
            is_system_audio=is_system_audio,
        ),
        **build_runtime_values(
            profile_data=profile_data,
            settings=settings,
            is_system_audio=is_system_audio,
        ),
    }
