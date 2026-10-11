"""벤치마크 스크립트 공용 계산·출력 helper. 외부 상태를 건드리지 않는 순수 함수만 둔다."""

from __future__ import annotations

import json
import statistics
import time


def _percentile(values: list[float], percentile: int) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return round(values[0], 2)
    quantiles = statistics.quantiles(values, n=100, method="inclusive")
    return round(quantiles[percentile - 1], 2)


def _round_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 4)


def emit_payload(*, text: str, is_final: bool, started_at: float) -> None:
    payload = {
        "text": text,
        "is_final": is_final,
        "emission_time": round(time.perf_counter() - started_at, 4),
    }
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def normalize_text(text: str) -> str:
    return " ".join(text.split()).strip()
