"""입력 소스 정책 프로파일 로더."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=8)
def load_audio_source_profiles(path: str) -> dict[str, dict[str, object]]:
    """오디오 입력 소스 프로파일 JSON을 로드한다."""

    return json.loads(Path(path).read_text(encoding="utf-8-sig"))
