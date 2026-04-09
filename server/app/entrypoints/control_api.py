"""Control API 전용 엔트리포인트."""

from server.app.app_factory import create_app


app = create_app(
    include_control_routes=True,
    include_live_routes=False,
    enable_live_runtime=False,
    enable_startup_recovery=True,
    process_report_jobs_inline=False,
)
