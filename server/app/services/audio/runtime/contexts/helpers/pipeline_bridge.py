"""오디오 영역의 pipeline bridge 서비스를 제공한다."""
from __future__ import annotations

import inspect


def process_preview_chunk(context, chunk: bytes):
    """preview chunk를 pipeline preview 경로로 전달한다."""

    process_preview = getattr(context.pipeline_service, "process_preview_chunk", None)
    if callable(process_preview):
        preview_kwargs: dict[str, int | None] = {}
        if "preview_cycle_id" in inspect.signature(process_preview).parameters:
            preview_kwargs["preview_cycle_id"] = context.active_preview_cycle_id
        return process_preview(
            context.session_id,
            chunk,
            context.input_source,
            **preview_kwargs,
        )
    return []


def process_final_chunk(context, chunk: bytes):
    """final chunk를 pipeline final 또는 legacy process_chunk로 전달한다."""

    process_final = getattr(context.pipeline_service, "process_final_chunk", None)
    if callable(process_final):
        return process_final(
            context.session_id,
            chunk,
            context.input_source,
        )
    return context.pipeline_service.process_chunk(
        context.session_id,
        chunk,
        context.input_source,
    )


def reset_stream(context) -> None:
    """pipeline의 runtime stream 상태를 초기화한다."""

    reset_runtime_streams = getattr(context.pipeline_service, "reset_runtime_streams", None)
    if callable(reset_runtime_streams):
        reset_runtime_streams()
        return

    speech_to_text_service = getattr(context.pipeline_service, "_speech_to_text_service", None)
    reset_stream_fn = getattr(speech_to_text_service, "reset_stream", None)
    if callable(reset_stream_fn):
        reset_stream_fn()
