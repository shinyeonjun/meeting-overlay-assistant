"""애플리케이션 로깅 설정."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path


class JsonLogFormatter(logging.Formatter):
    """구조화 로그를 위한 JSON 포매터."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(
    *,
    level: str = "INFO",
    use_json: bool = False,
    log_file_path: Path | None = None,
) -> None:
    """루트 로거를 한 번만 초기화한다."""
    root_logger = logging.getLogger()
    if getattr(root_logger, "_meeting_overlay_configured", False):
        for handler in root_logger.handlers:
            if getattr(handler, "_meeting_overlay_stream_handler", False):
                handler.setStream(sys.__stderr__)
        root_logger.setLevel(level.upper())
        return

    if use_json:
        formatter: logging.Formatter = JsonLogFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handlers: list[logging.Handler] = []
    stream_handler = logging.StreamHandler(sys.__stderr__)
    stream_handler._meeting_overlay_stream_handler = True  # type: ignore[attr-defined]
    stream_handler.setFormatter(formatter)
    handlers.append(stream_handler)

    if log_file_path is not None:
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler._meeting_overlay_file_handler = True  # type: ignore[attr-defined]
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    for handler in handlers:
        root_logger.addHandler(handler)
    root_logger.setLevel(level.upper())
    root_logger._meeting_overlay_configured = True  # type: ignore[attr-defined]
