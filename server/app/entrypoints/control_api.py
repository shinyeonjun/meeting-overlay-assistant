"""Control API 전용 엔트리포인트.

이 프로세스는 세션/워크스페이스/리포트 같은 제어면 API만 노출한다.
live 오디오 runtime은 포함하지 않아서, 브라우저나 워커가 붙는 관리용
서버를 가볍게 띄우고 싶을 때 사용한다.
"""

from server.app.app_factory import create_app


app = create_app(
    include_control_routes=True,
    include_live_routes=False,
    enable_live_runtime=False,
    enable_startup_recovery=True,
    process_report_jobs_inline=False,
)
