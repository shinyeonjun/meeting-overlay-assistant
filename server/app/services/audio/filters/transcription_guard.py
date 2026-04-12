"""전사 결과 품질 필터."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from server.app.services.audio.filters.transcription_guard_helpers import (
    compile_boundary_pattern,
    contains_blocked_phrase,
    is_boundary_only,
    is_high_no_speech_prob,
    is_language_inconsistent,
    is_too_short_for_confidence,
    looks_repetitive,
    normalize_text,
)
from server.app.services.audio.stt.transcription import TranscriptionResult


DEFAULT_TRANSCRIPTION_GUARD_PATH = (
    Path(__file__).resolve().parents[4] / "server" / "config" / "transcription_guard.json"
)


@dataclass(frozen=True)
class TranscriptionGuardConfig:
    """전사 필터 설정."""

    min_confidence: float = 0.35
    short_text_min_confidence: float = 0.6
    min_compact_length: int = 2
    max_repeat_ratio: float = 0.6
    max_consecutive_repeat: int = 4
    min_repetition_tokens: int = 6
    boundary_terms: tuple[str, ...] = ("끝", "종료", "완료")
    blocked_phrases: tuple[str, ...] = ()
    blocked_patterns: tuple[str, ...] = ()
    blocked_phrase_max_confidence: float = 0.8
    token_split_pattern: str = r"[\s,./!?;:()\[\]{}<>\"'`~|]+"
    expected_language: str | None = None
    language_consistency_enabled: bool = False
    language_consistency_max_confidence: float = 0.8
    min_target_script_ratio: float = 0.0
    min_letter_ratio: float = 0.0
    max_no_speech_prob: float | None = None

    @classmethod
    def with_patterns_from_path(
        cls,
        path: str | Path,
        **overrides,
    ) -> "TranscriptionGuardConfig":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            boundary_terms=tuple(data["boundary_terms"]),
            blocked_phrases=tuple(data.get("blocked_phrases", [])),
            blocked_patterns=tuple(data.get("blocked_patterns", [])),
            blocked_phrase_max_confidence=float(
                data.get("blocked_phrase_max_confidence", overrides.get("blocked_phrase_max_confidence", 0.8))
            ),
            token_split_pattern=data["token_split_pattern"],
            **overrides,
        )


class TranscriptionGuard:
    """저품질 전사를 이벤트 단계에서 걸러낸다."""

    def __init__(self, config: TranscriptionGuardConfig) -> None:
        self._config = config
        self._boundary_only_pattern = compile_boundary_pattern(config.boundary_terms)
        self._token_split_pattern = re.compile(config.token_split_pattern)
        self._blocked_patterns = tuple(
            re.compile(pattern, re.IGNORECASE)
            for pattern in config.blocked_patterns
        )

    def should_keep(self, result: TranscriptionResult) -> bool:
        """전사를 유지할지 여부를 반환한다."""

        keep, _reason = self.evaluate(result)
        return keep

    def evaluate(self, result: TranscriptionResult) -> tuple[bool, str | None]:
        """전사를 유지할지와 차단 이유를 함께 반환한다."""

        text = normalize_text(result.text)
        if not text:
            return False, "empty_text"
        if result.confidence < self._config.min_confidence:
            return False, "low_confidence"
        if contains_blocked_phrase(
            config=self._config,
            blocked_patterns=self._blocked_patterns,
            text=text,
            confidence=result.confidence,
        ):
            return False, "blocked_phrase"
        if is_high_no_speech_prob(config=self._config, result=result):
            return False, "high_no_speech_prob"
        if is_boundary_only(boundary_only_pattern=self._boundary_only_pattern, text=text):
            return False, "boundary_only"
        if is_too_short_for_confidence(
            config=self._config,
            text=text,
            confidence=result.confidence,
        ):
            return False, "too_short_for_confidence"
        if is_language_inconsistent(
            config=self._config,
            text=text,
            confidence=result.confidence,
        ):
            return False, "language_inconsistent"
        if looks_repetitive(
            config=self._config,
            token_split_pattern=self._token_split_pattern,
            text=text,
        ):
            return False, "repetitive"
        return True, None
