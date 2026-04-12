"""리포트 영역의   init   서비스를 제공한다."""
from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "ReportGenerationService",
    "ReportGenerationJobService",
    "ReportQueryService",
    "ReportService",
    "create_report_refiner",
]


def __getattr__(name: str) -> Any:
    if name == "ReportService":
        return import_module("server.app.services.reports.core.report_service").ReportService
    if name == "ReportGenerationService":
        return import_module(
            "server.app.services.reports.generation.report_generation_service"
        ).ReportGenerationService
    if name == "ReportGenerationJobService":
        return import_module(
            "server.app.services.reports.jobs.report_generation_job_service"
        ).ReportGenerationJobService
    if name == "ReportQueryService":
        return import_module(
            "server.app.services.reports.query.report_query_service"
        ).ReportQueryService
    if name == "create_report_refiner":
        return import_module(
            "server.app.services.reports.refinement.report_refiner_factory"
        ).create_report_refiner
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
