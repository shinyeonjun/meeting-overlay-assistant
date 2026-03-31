"""규칙 기반 분석 설정 로더."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AnalysisRuleConfig:
    """규칙 기반 분석기 설정."""

    question_patterns: tuple[str, ...]
    decision_keywords: tuple[str, ...]
    action_keywords: tuple[str, ...]
    due_date_patterns: tuple[str, ...]
    assignee_patterns: tuple[str, ...]
    risk_keywords: tuple[str, ...]
    enable_topic_events: bool
    topic_minimum_length: int
    topic_minimum_token_count: int
    topic_minimum_unique_token_count: int
    topic_max_numeric_ratio: float
    topic_blocked_patterns: tuple[str, ...]
    topic_title_max_length: int
    topic_group_max_length: int

    @classmethod
    def from_path(cls, path: Path) -> "AnalysisRuleConfig":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            question_patterns=tuple(data["question_patterns"]),
            decision_keywords=tuple(data["decision_keywords"]),
            action_keywords=tuple(data["action_keywords"]),
            due_date_patterns=tuple(data["due_date_patterns"]),
            assignee_patterns=tuple(data["assignee_patterns"]),
            risk_keywords=tuple(data["risk_keywords"]),
            enable_topic_events=bool(data.get("enable_topic_events", False)),
            topic_minimum_length=int(data["topic_minimum_length"]),
            topic_minimum_token_count=int(data["topic_minimum_token_count"]),
            topic_minimum_unique_token_count=int(data["topic_minimum_unique_token_count"]),
            topic_max_numeric_ratio=float(data["topic_max_numeric_ratio"]),
            topic_blocked_patterns=tuple(data["topic_blocked_patterns"]),
            topic_title_max_length=int(data["topic_title_max_length"]),
            topic_group_max_length=int(data["topic_group_max_length"]),
        )


def load_analysis_rule_config(path: str | Path) -> AnalysisRuleConfig:
    """분석 규칙 설정 파일을 읽는다."""
    return AnalysisRuleConfig.from_path(Path(path))
