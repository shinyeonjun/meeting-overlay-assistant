"""전사 가드 테스트."""

from server.app.services.audio.stt.transcription import TranscriptionResult
from server.app.services.audio.filters.transcription_guard import (
    TranscriptionGuard,
    TranscriptionGuardConfig,
)
from tests.fixtures.support.sample_inputs import QUESTION_TEXT


class TestTranscriptionGuard:
    def test_정상적인_문장은_통과한다(self):
        guard = TranscriptionGuard(TranscriptionGuardConfig())

        assert guard.should_keep(TranscriptionResult(text=QUESTION_TEXT, confidence=0.72))

    def test_낮은_confidence는_걸러낸다(self):
        guard = TranscriptionGuard(TranscriptionGuardConfig())

        assert not guard.should_keep(TranscriptionResult(text="오늘", confidence=0.22))

    def test_경계_토큰만_있는_문장은_걸러낸다(self):
        guard = TranscriptionGuard(TranscriptionGuardConfig())

        assert not guard.should_keep(TranscriptionResult(text="[끝]", confidence=0.5))
        assert not guard.should_keep(TranscriptionResult(text="-완료-", confidence=0.7))

    def test_반복이_심한_문장은_걸러낸다(self):
        guard = TranscriptionGuard(TranscriptionGuardConfig())
        repeated = " ".join(["끝까지"] * 20)

        assert not guard.should_keep(TranscriptionResult(text=repeated, confidence=0.83))

    def test_환각_블랙리스트_문장은_걸러낸다(self):
        guard = TranscriptionGuard(
            TranscriptionGuardConfig(
                blocked_phrases=("다음 영상에서 만나요", "thank you for watching"),
                blocked_phrase_max_confidence=0.8,
            )
        )

        assert not guard.should_keep(
            TranscriptionResult(text="다음 영상에서 만나요", confidence=0.62)
        )
        assert not guard.should_keep(
            TranscriptionResult(text="Thank you for watching", confidence=0.71)
        )
        assert guard.should_keep(
            TranscriptionResult(text="다음 영상에서 만나요", confidence=0.91)
        )

    def test_generic_credit_outro_regex도_걸러낸다(self):
        guard = TranscriptionGuard(
            TranscriptionGuardConfig(
                blocked_patterns=(
                    r"(?:한글\s*)?자막\s*by\s+\S+",
                    r"(?:시청해\s*주셔서|봐\s*주셔서)\s*감사합니다",
                    r"(?:한글\s*)?자막\s*제공(?:\s+및\s+자막\s*제공)?(?:\s+및\s+광고(?:를)?\s*포함하고\s*있습니다)?",
                ),
                blocked_phrase_max_confidence=0.8,
            )
        )

        assert not guard.should_keep(
            TranscriptionResult(text="한글자막 by 한효정", confidence=0.42)
        )
        assert not guard.should_keep(
            TranscriptionResult(text="시청해 주셔서 감사합니다", confidence=0.55)
        )
        assert not guard.should_keep(
            TranscriptionResult(
                text="한글자막 제공 및 자막 제공 및 광고를 포함하고 있습니다.",
                confidence=0.51,
            )
        )

    def test_한국어_세션에서_낮은_confidence의_외국어는_걸러낸다(self):
        guard = TranscriptionGuard(
            TranscriptionGuardConfig(
                expected_language="ko",
                language_consistency_enabled=True,
                language_consistency_max_confidence=0.75,
                min_target_script_ratio=0.25,
                min_letter_ratio=0.45,
            )
        )

        assert not guard.should_keep(
            TranscriptionResult(text="I threw a wish", confidence=0.48)
        )
        assert not guard.should_keep(
            TranscriptionResult(text="普通にいざと吐き出した大きさ", confidence=0.56)
        )
        assert guard.should_keep(
            TranscriptionResult(text="이거 사파리에서만 재현되는 거 맞아요?", confidence=0.62)
        )

    def test_no_speech_prob가_높으면_걸러낸다(self):
        guard = TranscriptionGuard(
            TranscriptionGuardConfig(
                max_no_speech_prob=0.55,
            )
        )

        assert not guard.should_keep(
            TranscriptionResult(
                text="감사합니다",
                confidence=0.78,
                no_speech_prob=0.83,
            )
        )
        assert guard.should_keep(
            TranscriptionResult(
                text="회의를 시작하겠습니다",
                confidence=0.78,
                no_speech_prob=0.12,
            )
        )


