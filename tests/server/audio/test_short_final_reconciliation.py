"""짧은 구간 확정 자막과 회색 자막 대조 테스트."""

from __future__ import annotations

from server.app.contexts.live_capture import SpeechSegment, TranscriptionResult
from server.app.contexts.live_capture.application.audio.pipeline.final.helpers.persistence import (
    reconcile_short_final_with_live,
)


class _CoordinationState:
    def __init__(self, candidates: dict[str, str]) -> None:
        self._candidates = candidates

    def peek_live_final_candidate(self, *, segment_id: str):
        text = self._candidates.get(segment_id)
        return {"text": text, "emitted_at_ms": 0} if text is not None else None


class _Service:
    def __init__(self, candidates: dict[str, str]) -> None:
        self._coordination_state = _CoordinationState(candidates)


def _segment(duration_ms: int) -> SpeechSegment:
    return SpeechSegment(raw_bytes=b"", start_ms=1_000, end_ms=1_000 + duration_ms)


def _reconcile(*, live: str | None, final: str, duration_ms: int = 2_000, confidence: float = 0.9):
    candidates = {"seg-1": live} if live is not None else {}
    return reconcile_short_final_with_live(
        _Service(candidates),
        session_id="s",
        segment=_segment(duration_ms),
        segment_id="seg-1",
        transcription=TranscriptionResult(text=final, confidence=confidence),
    )


def test_짧은_구간에서_회색_자막과_전혀_다르면_회색_자막을_쓴다() -> None:
    # 실기에서 본 사례: 회색 자막은 맞게 들었고 whisper는 "감사합니다."를 지어냈다.
    result = _reconcile(live="포클랜드 파운드이다.", final="감사합니다.")

    assert result.text == "포클랜드 파운드이다."
    assert result.confidence == 0.5


def test_회색_자막과_비슷하면_확정_자막을_그대로_둔다() -> None:
    result = _reconcile(live="생개자를 소지하면", final="생겐 비자를 소지하면")

    assert result.text == "생겐 비자를 소지하면"
    assert result.confidence == 0.9


def test_확정_자막에_영문이나_숫자가_있으면_대조하지_않는다() -> None:
    # 실서버 측정에서 잘못 바뀐 사례: 확정이 맞고 회색 자막이 약어를 소리 나는 대로 적었다.
    assert _reconcile(live="에스 더블유 에이 피", final="SWAPO도").text == "SWAPO도"
    assert _reconcile(live="오후 열시", final="오후 10시").text == "오후 10시"


def test_긴_구간은_대조하지_않는다() -> None:
    result = _reconcile(live="포클랜드 파운드이다.", final="감사합니다.", duration_ms=3_500)

    assert result.text == "감사합니다."


def test_회색_자막이_너무_짧거나_없으면_대조하지_않는다() -> None:
    assert _reconcile(live="네", final="감사합니다.").text == "감사합니다."
    assert _reconcile(live=None, final="감사합니다.").text == "감사합니다."


def test_구간_짝이_없으면_대조하지_않는다() -> None:
    result = reconcile_short_final_with_live(
        _Service({"seg-1": "포클랜드 파운드이다."}),
        session_id="s",
        segment=_segment(2_000),
        segment_id=None,
        transcription=TranscriptionResult(text="감사합니다.", confidence=0.9),
    )

    assert result.text == "감사합니다."
