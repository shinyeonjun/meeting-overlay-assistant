"""호환 경로용 reports worker 래퍼."""

from server.app.workers.report.generation_worker import (
    build_default_worker_id,
    build_parser,
    main,
    run_once,
)

__all__ = [
    "build_default_worker_id",
    "build_parser",
    "main",
    "run_once",
]


if __name__ == "__main__":
    raise SystemExit(main())
