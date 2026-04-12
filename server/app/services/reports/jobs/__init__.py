"""리포트 영역의   init   서비스를 제공한다."""
from server.app.services.reports.jobs.report_generation_job_service import (
    ReportGenerationJobService,
)

__all__ = ["ReportGenerationJobService"]
