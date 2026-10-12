"""라이브 확정 경로 analyzer 선택 테스트."""

from __future__ import annotations

from server.app.api.http.wiring.shared_service_providers import audio as audio_providers
from server.app.api.http.wiring.shared_service_providers.analysis import get_live_inline_analyzer


def test_라이브_파이프라인은_LLM을_부르지_않는_analyzer를_쓴다(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_build(**kwargs):
        captured.update(kwargs)
        return "pipeline"

    monkeypatch.setattr(audio_providers.audio_runtime, "build_audio_pipeline_service", fake_build)
    for name in (
        "get_speech_to_text_service",
        "get_utterance_repository",
        "get_event_repository",
        "get_transaction_manager",
        "get_runtime_monitor_service",
        "get_shared_live_event_corrector",
        "get_shared_live_question_dispatcher",
    ):
        monkeypatch.setattr(audio_providers, name, lambda *args, **kwargs: object())

    assert audio_providers.build_audio_pipeline_service("system_audio") == "pipeline"

    analyzer = captured["analyzer_service"]
    assert analyzer is get_live_inline_analyzer()
    assert type(analyzer).__name__ == "RuleBasedMeetingAnalyzer"
