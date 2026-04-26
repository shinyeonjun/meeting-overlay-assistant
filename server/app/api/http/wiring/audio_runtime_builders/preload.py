"""audio runtime preload 관련 helper."""

from __future__ import annotations

from server.app.domain.shared.enums import AudioSource


def preload_runtime_services(
    *,
    settings,
    logger,
    resolve_speech_to_text_profile,
    resolve_stt_settings_for_source,
    mark_source_pending,
    mark_source_ready,
    mark_source_failed,
    finalize_runtime_readiness,
    create_speech_to_text_service,
) -> None:
    """애플리케이션 시작 시 공용 STT 서비스를 preload한다."""

    if not settings.stt_preload_on_startup:
        finalize_runtime_readiness()
        return None

    sources = []
    if (
        settings.mic_server_stt_fallback_enabled
        and settings.mic_server_stt_preload_enabled
    ):
        sources.append(AudioSource.MIC.value)
    if settings.stt_backend_system_audio:
        sources.append(AudioSource.SYSTEM_AUDIO.value)

    for source in sources:
        profile = resolve_speech_to_text_profile(resolve_stt_settings_for_source(source))
        mark_source_pending(
            source,
            backend=profile.backend_name,
            shared_instance=profile.shared_instance,
        )
        service = create_speech_to_text_service(source)
        preload = getattr(service, "preload", None)
        if callable(preload):
            try:
                preload()
                mark_source_ready(source)
            except Exception:
                mark_source_failed(source, "preload_failed")
                logger.exception(
                    "STT preload 실패. source=%s 에서는 lazy-load 경로로 전환합니다.",
                    source,
                )
        else:
            mark_source_ready(source)

    finalize_runtime_readiness()
    return None
