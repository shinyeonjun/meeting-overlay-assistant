"""미디어 서비스 프로파일 로더."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=1)
def load_media_service_profiles(config_path: str) -> dict[str, Any]:
    """미디어 서비스 프로파일 JSON을 로드한다."""

    return json.loads(Path(config_path).read_text(encoding="utf-8-sig"))
