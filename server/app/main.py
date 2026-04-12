"""기본 통합 서버 엔트리포인트."""

from server.app.app_factory import create_app


app = create_app(
    include_control_routes=True,
    include_live_routes=True,
    enable_live_runtime=True,
    process_report_jobs_inline=True,
)
