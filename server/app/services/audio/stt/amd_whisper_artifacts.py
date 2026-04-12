"""오디오 영역의 amd whisper artifacts 서비스를 제공한다."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AMDWhisperArtifacts:
    """AMD Whisper 실행에 필요한 파일 경로 묶음."""

    encoder_model_path: Path | None
    decoder_model_path: Path | None
    encoder_rai_path: Path | None

    def missing_paths(self) -> tuple[str, ...]:
        """누락된 필수 경로 이름을 반환한다."""
        missing: list[str] = []
        if self.encoder_model_path is None or not self.encoder_model_path.exists():
            missing.append("STT_ENCODER_MODEL_PATH")
        if self.decoder_model_path is None or not self.decoder_model_path.exists():
            missing.append("STT_DECODER_MODEL_PATH")
        return tuple(missing)

    @property
    def is_ready(self) -> bool:
        """실행에 필요한 경로가 모두 존재하는지 반환한다."""
        return not self.missing_paths()

    @property
    def has_encoder_rai(self) -> bool:
        """선택형 encoder RAI 파일이 준비됐는지 반환한다."""
        return self.encoder_rai_path is not None and self.encoder_rai_path.exists()
