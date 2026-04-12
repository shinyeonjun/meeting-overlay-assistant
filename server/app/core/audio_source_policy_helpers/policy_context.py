"""Audio source policy 계산용 공통 context helper."""

from __future__ import annotations

from server.app.domain.shared.enums import AudioSource


def build_policy_context(
    *,
    source: str,
    settings,
    profiles: dict[str, dict[str, object]],
) -> tuple[bool, dict[str, object]]:
    """입력 source에 맞는 공통 계산 context를 만든다."""

    is_system_audio = source in (
        AudioSource.SYSTEM_AUDIO.value,
        AudioSource.MIC_AND_AUDIO.value,
    )
    profile_data = {
        **profiles.get("default", {}),
        **profiles.get(source, {}),
    }
    use_vad_default = source in {
        AudioSource.MIC.value,
        AudioSource.SYSTEM_AUDIO.value,
        AudioSource.MIC_AND_AUDIO.value,
    }
    profile_data.setdefault("use_vad", use_vad_default)
    return is_system_audio, profile_data
