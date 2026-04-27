"""회의록 산출물에서 공유하는 시간 구간 포맷터."""

from __future__ import annotations


def format_timeline_range(start_ms: int, end_ms: int) -> str:
    """밀리초 구간을 mm:ss-mm:ss 문자열로 변환한다."""

    return f"{format_mmss(start_ms)}-{format_mmss(end_ms)}"


def format_mmss(value_ms: int) -> str:
    """밀리초를 mm:ss 문자열로 변환한다."""

    total_seconds = max(int(value_ms // 1000), 0)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"
