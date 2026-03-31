from __future__ import annotations

import json
from dataclasses import replace

from server.app.core.config import settings
from server.app.core.media_service_profiles import (
    resolve_audio_preprocessor_profile,
    resolve_speaker_diarizer_profile,
    resolve_speech_to_text_profile,
)


class TestMediaServiceProfiles:
    def test_stt_profile은_기본_stt_설정을_해석한다(self):
        profile = resolve_speech_to_text_profile(settings)

        assert profile.backend_name
        assert profile.model_id
        assert profile.sample_rate_hz == settings.stt_sample_rate_hz

    def test_moonshine_streaming_profile은_partial_설정을_해석한다(self):
        test_settings = replace(settings, stt_backend="moonshine_streaming")

        profile = resolve_speech_to_text_profile(test_settings)

        assert profile.backend_name == "moonshine_streaming"
        assert profile.model_id == "moonshine/tiny-ko"
        assert profile.shared_instance is False
        assert profile.partial_buffer_ms == 900
        assert profile.partial_emit_interval_ms == 240
        assert profile.partial_min_rms_threshold == 0.004

    def test_faster_whisper_streaming_profile은_partial_설정을_해석한다(self):
        test_settings = replace(settings, stt_backend="faster_whisper_streaming")

        profile = resolve_speech_to_text_profile(test_settings)

        assert profile.backend_name == "faster_whisper_streaming"
        assert profile.shared_instance is False
        assert profile.partial_buffer_ms == 760
        assert profile.partial_emit_interval_ms == 120
        assert profile.partial_min_growth_chars == 1
        assert profile.partial_backtrack_tolerance_chars == 4
        assert profile.partial_commit_min_chars_without_boundary == 2
        assert profile.initial_prompt == settings.stt_initial_prompt

    def test_hybrid_local_streaming_profile은_partial_final_backend를_분리해_해석한다(self):
        test_settings = replace(settings, stt_backend="hybrid_local_streaming")

        profile = resolve_speech_to_text_profile(test_settings)

        assert profile.backend_name == "hybrid_local_streaming"
        assert profile.shared_instance is False
        assert profile.partial_backend_name == "faster_whisper_streaming"
        assert profile.final_backend_name == "faster_whisper"
        assert profile.partial_model_id == "deepdml/faster-whisper-large-v3-turbo-ct2"
        assert profile.final_model_id == "deepdml/faster-whisper-large-v3-turbo-ct2"

    def test_hybrid_local_streaming_sherpa_profile은_partial_안정화_설정을_해석한다(self):
        test_settings = replace(settings, stt_backend="hybrid_local_streaming_sherpa")

        profile = resolve_speech_to_text_profile(test_settings)

        assert profile.backend_name == "hybrid_local_streaming"
        assert profile.partial_backend_name == "sherpa_onnx_streaming"
        assert profile.partial_emit_interval_ms == 140
        assert profile.partial_agreement_window == 2
        assert profile.partial_agreement_min_count == 2
        assert profile.partial_min_stable_chars == 3
        assert profile.partial_min_growth_chars == 2
        assert profile.partial_backtrack_tolerance_chars == 2
        assert profile.partial_commit_min_chars_without_boundary == 3

    def test_partial_profile값이_없으면_app_config_기본값으로_대체한다(self, tmp_path):
        config_path = tmp_path / "media_service_profiles.json"
        config_path.write_text(
            json.dumps(
                {
                    "speech_to_text": {
                        "faster_whisper_streaming": {
                            "backend_name": "faster_whisper_streaming",
                            "model_id": "deepdml/faster-whisper-large-v3-turbo-ct2",
                        }
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        test_settings = replace(
            settings,
            stt_backend="faster_whisper_streaming",
            media_service_profiles_config_path=config_path,
            partial_buffer_ms=111,
            partial_emit_interval_ms=222,
            partial_min_rms_threshold=0.123,
            partial_agreement_window=4,
            partial_agreement_min_count=3,
            partial_min_stable_chars=5,
            partial_min_growth_chars=6,
            partial_backtrack_tolerance_chars=7,
            partial_commit_min_chars_without_boundary=8,
        )

        profile = resolve_speech_to_text_profile(test_settings)

        assert profile.partial_buffer_ms == 111
        assert profile.partial_emit_interval_ms == 222
        assert profile.partial_min_rms_threshold == 0.123
        assert profile.partial_agreement_window == 4
        assert profile.partial_agreement_min_count == 3
        assert profile.partial_min_stable_chars == 5
        assert profile.partial_min_growth_chars == 6
        assert profile.partial_backtrack_tolerance_chars == 7
        assert profile.partial_commit_min_chars_without_boundary == 8

    def test_audio_preprocessor_profile은_전처리기_설정을_해석한다(self):
        profile = resolve_audio_preprocessor_profile(settings)

        assert profile.backend_name
        assert profile.atten_lim_db > 0

    def test_speaker_diarizer_profile은_worker_설정까지_해석한다(self):
        profile = resolve_speaker_diarizer_profile(settings)

        assert profile.backend_name
        assert profile.model_id
