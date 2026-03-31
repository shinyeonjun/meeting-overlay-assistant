"""Live runtime API 전용 엔트리포인트."""

from server.app.app_factory import create_app


app = create_app(
    include_control_routes=False,
    include_live_routes=True,
    enable_live_runtime=True,
    process_report_jobs_inline=False,
)
