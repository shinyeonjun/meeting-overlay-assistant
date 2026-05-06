"""assistant 시간 문맥 모델."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python 3.9+ 기본 경로
    ZoneInfo = None

KST_TIMEZONE_NAME = "Asia/Seoul"
KST_OFFSET = timezone(timedelta(hours=9), name="KST")


@dataclass(frozen=True)
class AssistantTimeContext:
    """상대 시간 질문 해석에 사용할 현재 시각 문맥."""

    now: datetime
    timezone_name: str = KST_TIMEZONE_NAME

    @classmethod
    def now_kst(cls) -> "AssistantTimeContext":
        """현재 KST 기준 시간 문맥을 만든다."""

        tzinfo = _load_kst_timezone()
        return cls(now=datetime.now(tzinfo), timezone_name=KST_TIMEZONE_NAME)

    def render_for_prompt(self) -> str:
        """LLM 프롬프트에 넣을 시간 문맥 문자열을 만든다."""

        return "\n".join(
            [
                f"- 현재 사용자 시간: {self.now.strftime('%Y-%m-%d %H:%M:%S')} KST",
                f"- 시간대: {self.timezone_name}",
                "- 상대 날짜 표현(오늘, 어제, 이번 주, 최근)은 위 시간을 기준으로 해석한다.",
                "- 저장 데이터 timestamp가 UTC일 수 있으므로 답변에서는 근거의 실제 표시 시간을 우선한다.",
            ]
        )


def _load_kst_timezone():
    if ZoneInfo is None:
        return KST_OFFSET
    try:
        return ZoneInfo(KST_TIMEZONE_NAME)
    except Exception:
        return KST_OFFSET
