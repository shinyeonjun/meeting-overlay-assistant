"""AMD Whisper 아티팩트 검증 테스트."""

from pathlib import Path

from backend.app.services.audio.stt.amd_whisper_artifacts import AMDWhisperArtifacts


class TestAMDWhisperArtifacts:
    """AMD Whisper 아티팩트 상태를 검증한다."""

    def test_필수_파일이_없으면_누락_환경변수를_반환한다(self):
        artifacts = AMDWhisperArtifacts(
            encoder_model_path=None,
            decoder_model_path=None,
            encoder_rai_path=None,
        )

        assert artifacts.missing_paths() == (
            "STT_ENCODER_MODEL_PATH",
            "STT_DECODER_MODEL_PATH",
        )
        assert artifacts.is_ready is False
        assert artifacts.has_encoder_rai is False

    def test_필수_파일이_있으면_ready를_반환한다(self, tmp_path: Path):
        encoder = tmp_path / "encoder_model.onnx"
        decoder = tmp_path / "decoder_model.onnx"
        encoder.write_text("stub", encoding="utf-8")
        decoder.write_text("stub", encoding="utf-8")

        artifacts = AMDWhisperArtifacts(
            encoder_model_path=encoder,
            decoder_model_path=decoder,
            encoder_rai_path=None,
        )

        assert artifacts.missing_paths() == ()
        assert artifacts.is_ready is True
        assert artifacts.has_encoder_rai is False

    def test_선택형_encoder_rai가_있으면_has_encoder_rai를_참으로_반환한다(self, tmp_path: Path):
        encoder = tmp_path / "encoder_model.onnx"
        decoder = tmp_path / "decoder_model.onnx"
        encoder_rai = tmp_path / "ggml-small-encoder-vitisai.rai"
        encoder.write_text("stub", encoding="utf-8")
        decoder.write_text("stub", encoding="utf-8")
        encoder_rai.write_text("stub", encoding="utf-8")

        artifacts = AMDWhisperArtifacts(
            encoder_model_path=encoder,
            decoder_model_path=decoder,
            encoder_rai_path=encoder_rai,
        )

        assert artifacts.is_ready is True
        assert artifacts.has_encoder_rai is True

