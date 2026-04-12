"""오디오 영역의 test preview utterance building 동작을 검증한다."""
from __future__ import annotations

from server.app.services.audio.pipeline.preview.preview_helpers.utterance_building import (
    build_preview_utterance_payloads,
)
from server.app.services.audio.stt.transcription import TranscriptionResult


class _AlwaysPassGuard:
    def evaluate(self, result):  # noqa: ANN001
        return True, None


class _FakeCoordinationState:
    def __init__(self) -> None:
        self.marked: list[tuple[int, str, int]] = []
        self.live_final_candidates: list[tuple[str, str, int]] = []

    def get_or_create_preview_binding(self) -> tuple[int, str]:
        return 7, "seg-live-7"

    def mark_preview_emitted(self, *, seq_num: int, segment_id: str, now_ms: int) -> None:
        self.marked.append((seq_num, segment_id, now_ms))

    def remember_live_final_candidate(
        self,
        *,
        segment_id: str,
        text: str,
        emitted_at_ms: int,
    ) -> None:
        self.live_final_candidates.append((segment_id, text, emitted_at_ms))


class _FakeService:
    def __init__(self) -> None:
        self._transcription_guard = _AlwaysPassGuard()
        self._preview_min_compact_length = 1
        self._coordination_state = _FakeCoordinationState()
        self._runtime_monitor_service = None

    @staticmethod
    def _now_ms() -> int:
        return 1_234

    @staticmethod
    def _normalize_text(text: str) -> str:
        return " ".join(text.casefold().split())

    @staticmethod
    def _compact_length(text: str) -> int:
        return len("".join(ch for ch in text if ch.isalnum()))


class TestPreviewUtteranceBuilding:
    """PreviewUtteranceBuilding 동작을 검증한다."""
    def test_증분_preview는_마지막_후보만_남긴다(self) -> None:
        service = _FakeService()

        utterances = build_preview_utterance_payloads(
            service,
            session_id="session-1",
            input_source="system_audio",
            preview_cycle_id=11,
            preview_results=[
                TranscriptionResult(text="안녕", confidence=0.5, kind="preview", revision=1),
                TranscriptionResult(text="안녕하세요", confidence=0.7, kind="preview", revision=2),
            ],
        )

        assert len(utterances) == 1
        assert utterances[0].text == "안녕하세요"
        assert utterances[0].kind == "preview"
        assert utterances[0].revision == 2

    def test_preview와_live_final이_같이_오면_live_final만_남긴다(self) -> None:
        service = _FakeService()

        utterances = build_preview_utterance_payloads(
            service,
            session_id="session-1",
            input_source="system_audio",
            preview_cycle_id=11,
            preview_results=[
                TranscriptionResult(text="안녕하세요", confidence=0.6, kind="preview", revision=1),
                TranscriptionResult(text="안녕하세요", confidence=0.8, kind="live_final", revision=2),
            ],
        )

        assert len(utterances) == 1
        assert utterances[0].kind == "live_final"
        assert service._coordination_state.live_final_candidates == [
            ("seg-live-7", "안녕하세요", 1_234)
        ]

    def test_서로_다른_preview는_분리해_유지한다(self) -> None:
        service = _FakeService()

        utterances = build_preview_utterance_payloads(
            service,
            session_id="session-1",
            input_source="system_audio",
            preview_cycle_id=11,
            preview_results=[
                TranscriptionResult(text="첫 번째 문장", confidence=0.6, kind="preview", revision=1),
                TranscriptionResult(text="완전히 다른 안건", confidence=0.7, kind="preview", revision=2),
            ],
        )

        assert len(utterances) == 2
        assert utterances[0].text == "첫 번째 문장"
        assert utterances[1].text == "완전히 다른 안건"
