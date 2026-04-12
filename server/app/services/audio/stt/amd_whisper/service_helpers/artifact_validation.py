"""AMD Whisper artifact 검증 helper."""

from __future__ import annotations


def ensure_artifacts_ready(*, service) -> bool:
    """AMD Whisper artifact 경로가 준비됐는지 확인한다."""

    if service._artifacts_validated:
        return True

    missing_paths = service._artifacts.missing_paths()
    if missing_paths:
        raise RuntimeError(
            "amd_whisper_npu backend를 실행하려면 Whisper ONNX 아티팩트가 필요합니다. "
            f"비어있는 설정: {', '.join(missing_paths)}"
        )
    service._artifacts_validated = True
    service._logger.info("AMD Whisper 아티팩트 검증 완료: model_id=%s", service._config.model_id)
    return True
