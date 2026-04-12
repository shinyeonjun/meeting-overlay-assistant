"""공통 파이프라인에서 report generation worker 워커를 실행한다."""
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
