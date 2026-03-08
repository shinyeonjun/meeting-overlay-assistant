"""STT acceptance runner 테스트."""

from backend.experiments.stt.run_stt_acceptance import (
    AcceptanceThreshold,
    _resolve_acceptance_threshold_profile,
    evaluate_acceptance,
    evaluate_sample,
    merge_thresholds,
)


class TestSttAcceptanceRunner:
    def test_acceptance_profile을_읽을_수_있다(self):
        profile = _resolve_acceptance_threshold_profile("system_audio_default")

        assert profile["max_wer_kept"] == 0.35

    def test_threshold_merge는_override를_우선한다(self):
        merged = merge_thresholds(
            AcceptanceThreshold(max_wer_kept=0.3, max_cer_kept=0.2),
            AcceptanceThreshold(max_wer_kept=0.2),
        )

        assert merged.max_wer_kept == 0.2
        assert merged.max_cer_kept == 0.2

    def test_sample_evaluation은_초과_항목을_실패로_표시한다(self):
        failures = evaluate_sample(
            {
                "wer_kept": {"rate": 0.4},
                "cer_kept": {"rate": 0.1},
                "guard_keep_rate_vs_raw": 0.5,
                "rtf_end_to_end": 0.8,
            },
            AcceptanceThreshold(
                max_wer_kept=0.3,
                min_guard_keep_rate_vs_raw=0.9,
                max_rtf_end_to_end=0.5,
            ),
        )

        assert "wer_kept>0.3" in failures
        assert "guard_keep_rate_vs_raw<0.9" in failures
        assert "rtf_end_to_end>0.5" in failures

    def test_acceptance_evaluation은_전체_pass_fail을_계산한다(self):
        evaluation = evaluate_acceptance(
            result={
                "backend": "faster_whisper",
                "model_id": "model",
                "samples": [
                    {
                        "sample_name": "sample-1",
                        "wer_kept": {"rate": 0.2},
                        "cer_kept": {"rate": 0.1},
                        "guard_keep_rate_vs_raw": 1.0,
                        "rtf_end_to_end": 0.2,
                    }
                ],
                "aggregate": {
                    "avg_wer_kept": 0.2,
                    "avg_cer_kept": 0.1,
                    "avg_guard_keep_rate_vs_raw": 1.0,
                    "avg_rtf_end_to_end": 0.2,
                },
            },
            samples=[{"name": "sample-1"}],
            default_threshold=AcceptanceThreshold(
                max_wer_kept=0.3,
                max_cer_kept=0.2,
                min_guard_keep_rate_vs_raw=0.9,
                max_rtf_end_to_end=0.5,
            ),
        )

        assert evaluation["passed"] is True
        assert evaluation["samples"][0]["passed"] is True
