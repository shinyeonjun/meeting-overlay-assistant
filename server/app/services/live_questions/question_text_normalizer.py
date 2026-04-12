"""실시간 질문 입력 텍스트 보정 helper."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from dataclasses import replace

from server.app.core.config_helpers.env import get_env
from server.app.services.live_questions.models import LiveQuestionUtterance


logger = logging.getLogger(__name__)

_ENV_NAME = "LIVE_QUESTION_TERM_ALIASES_JSON"


@dataclass(frozen=True, slots=True)
class QuestionTextNormalizer:
    """질문 lane에만 적용할 가벼운 텍스트 치환기."""

    replacements: tuple[tuple[str, str], ...] = ()

    def normalize_utterance(self, utterance: LiveQuestionUtterance) -> LiveQuestionUtterance:
        """질문 분석용 발화 텍스트를 가볍게 정규화한다."""

        if not self.replacements or not utterance.text:
            return utterance

        text = utterance.text
        for source, target in self.replacements:
            if source in text:
                text = text.replace(source, target)

        if text == utterance.text:
            return utterance

        return replace(utterance, text=text)


def load_question_text_normalizer_from_env() -> QuestionTextNormalizer:
    """환경 변수에 지정된 질문 lane 전용 치환 사전을 불러온다."""

    raw = get_env(_ENV_NAME)
    if raw is None:
        return QuestionTextNormalizer()

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("질문 lane 도메인 치환 사전 파싱 실패: env=%s", _ENV_NAME)
        return QuestionTextNormalizer()

    replacements: list[tuple[str, str]] = []
    if isinstance(payload, dict):
        items = payload.items()
    elif isinstance(payload, list):
        items = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            source = item.get("source")
            target = item.get("target")
            if source not in {None, ""} and target not in {None, ""}:
                replacements.append((str(source), str(target)))
    else:
        return QuestionTextNormalizer()

    if isinstance(payload, dict):
        for source, target in items:
            if source in {None, ""} or target in {None, ""}:
                continue
            replacements.append((str(source), str(target)))

    replacements.sort(key=lambda item: len(item[0]), reverse=True)
    return QuestionTextNormalizer(replacements=tuple(replacements))
