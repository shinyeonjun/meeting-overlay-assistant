"""전사 결과 품질 필터."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

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
        self._boundary_only_pattern = self._compile_boundary_pattern(config.boundary_terms)
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
        text = self._normalize_text(result.text)
        if not text:
            return False, "empty_text"
        if result.confidence < self._config.min_confidence:
            return False, "low_confidence"
        if self._contains_blocked_phrase(text, result.confidence):
            return False, "blocked_phrase"
        if self._is_high_no_speech_prob(result):
            return False, "high_no_speech_prob"
        if self._is_boundary_only(text):
            return False, "boundary_only"
        if self._is_too_short_for_confidence(text, result.confidence):
            return False, "too_short_for_confidence"
        if self._is_language_inconsistent(text, result.confidence):
            return False, "language_inconsistent"
        if self._looks_repetitive(text):
            return False, "repetitive"
        return True, None

    @staticmethod
    def _normalize_text(text: str) -> str:
        return " ".join(text.split())

    def _is_boundary_only(self, text: str) -> bool:
        return bool(self._boundary_only_pattern.fullmatch(text))

    def _contains_blocked_phrase(self, text: str, confidence: float) -> bool:
        if confidence > self._config.blocked_phrase_max_confidence:
            return False

        normalized = text.casefold()
        if any(
            blocked_phrase.casefold() in normalized
            for blocked_phrase in self._config.blocked_phrases
        ):
            return True
        return any(pattern.search(text) for pattern in self._blocked_patterns)

    def _is_high_no_speech_prob(self, result: TranscriptionResult) -> bool:
        if self._config.max_no_speech_prob is None:
            return False
        if result.no_speech_prob is None:
            return False
        return result.no_speech_prob > self._config.max_no_speech_prob

    def _is_too_short_for_confidence(self, text: str, confidence: float) -> bool:
        compact = re.sub(r"[\W_]+", "", text, flags=re.UNICODE)
        if len(compact) > self._config.min_compact_length:
            return False
        return confidence < self._config.short_text_min_confidence

    def _looks_repetitive(self, text: str) -> bool:
        tokens = [token for token in self._token_split_pattern.split(text) if token]
        if len(tokens) < self._config.min_repetition_tokens:
            return False

        token_counts: dict[str, int] = {}
        max_count = 0
        max_consecutive = 1
        current_consecutive = 1

        for index, token in enumerate(tokens):
            token_counts[token] = token_counts.get(token, 0) + 1
            max_count = max(max_count, token_counts[token])
            if index > 0 and token == tokens[index - 1]:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 1

        repeat_ratio = max_count / len(tokens)
        return (
            repeat_ratio >= self._config.max_repeat_ratio
            or max_consecutive >= self._config.max_consecutive_repeat
        )

    def _is_language_inconsistent(self, text: str, confidence: float) -> bool:
        if not self._config.language_consistency_enabled:
            return False
        if not self._config.expected_language:
            return False
        if confidence > self._config.language_consistency_max_confidence:
            return False

        expected_language = self._config.expected_language.casefold()
        script_counts = self._count_scripts(text)
        total_letter_count = sum(script_counts.values())
        if total_letter_count == 0:
            return False

        compact = re.sub(r"\s+", "", text)
        letter_ratio = total_letter_count / max(len(compact), 1)
        if letter_ratio < self._config.min_letter_ratio:
            return True

        target_count = self._select_target_script_count(expected_language, script_counts)
        target_ratio = target_count / total_letter_count
        if target_count == 0:
            return True
        return target_ratio < self._config.min_target_script_ratio

    @staticmethod
    def _count_scripts(text: str) -> dict[str, int]:
        counts = {
            "hangul": 0,
            "latin": 0,
            "japanese": 0,
        }
        for char in text:
            code = ord(char)
            if 0xAC00 <= code <= 0xD7A3 or 0x3131 <= code <= 0x318E:
                counts["hangul"] += 1
            elif (0x3040 <= code <= 0x30FF) or (0x4E00 <= code <= 0x9FFF):
                counts["japanese"] += 1
            elif ("A" <= char <= "Z") or ("a" <= char <= "z"):
                counts["latin"] += 1
        return counts

    @staticmethod
    def _select_target_script_count(
        expected_language: str,
        script_counts: dict[str, int],
    ) -> int:
        if expected_language.startswith("ko"):
            return script_counts["hangul"]
        if expected_language.startswith("en"):
            return script_counts["latin"]
        if expected_language.startswith("ja"):
            return script_counts["japanese"]
        return sum(script_counts.values())

    @staticmethod
    def _compile_boundary_pattern(boundary_terms: tuple[str, ...]) -> re.Pattern[str]:
        escaped_terms = "|".join(re.escape(term) for term in boundary_terms)
        return re.compile(
            rf"^[\s\[\]\(\)\-_.~]*({escaped_terms})[\s\[\]\(\)\-_.~]*$"
        )
