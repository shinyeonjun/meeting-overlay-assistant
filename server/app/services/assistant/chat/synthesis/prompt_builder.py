"""Assistant answer prompt construction."""

from __future__ import annotations

from server.app.domain.retrieval import RetrievalSearchResult
from server.app.services.assistant.chat.history_context import render_conversation_history
from server.app.services.assistant.chat.models import (
    AssistantQueryPlan,
    AssistantTimeContext,
)
from server.app.services.assistant.chat.synthesis.source_metadata import (
    render_source_metadata,
)
from server.app.services.assistant.chat.synthesis.text_limits import truncate_text


def build_system_prompt() -> str:
    """Build the system prompt for the evidence-grounded assistant."""

    return (
        "You are the CAPS meeting-data assistant. Answer only from the provided evidence. "
        "Always answer in Korean unless the user explicitly asks for another language. "
        "Never switch to Chinese, English, or mixed-language output for Korean questions. "
        "Focus on the user's actual question first. Do not invent sections, decisions, risks, "
        "action items, meetings, or dates. Keep answers concise: usually 1-3 sentences or a few bullets. "
        "Use citations such as [S1] only where they support a concrete statement. "
        "When evidence is insufficient, say so plainly."
    )


def build_user_prompt(
    *,
    plan: AssistantQueryPlan,
    sources: list[RetrievalSearchResult],
    time_context: AssistantTimeContext,
    conversation_history=(),
) -> str:
    """Render retrieved evidence and the query plan into the answer prompt."""

    lines = [
        "User question:",
        plan.query,
        "",
        "Retrieval query:",
        plan.search_query,
        "",
        "Current time context:",
        time_context.render_for_prompt(),
    ]
    history_text = render_conversation_history(conversation_history)
    if history_text:
        lines.extend(["", "Recent conversation:", history_text])
    if plan.answer_focus:
        lines.extend(["", "Answer focus:", plan.answer_focus])
    if plan.session_scope or plan.content_focuses:
        lines.extend(
            [
                "",
                "Structured retrieval intent:",
                f"- Session scope: {plan.session_scope or '-'}",
                f"- Requires knowledge: {plan.requires_knowledge}",
                f"- Content focuses: {', '.join(plan.content_focuses) if plan.content_focuses else '-'}",
            ]
        )
    if plan.time_expression or plan.resolved_time_range or plan.time_scope:
        lines.extend(
            [
                "",
                "Time interpretation:",
                f"- Original expression: {plan.time_expression or '-'}",
                f"- Resolved range: {plan.resolved_time_range or '-'}",
                f"- Scope: {plan.time_scope or '-'}",
            ]
        )

    lines.extend(["", "Retrieved evidence:"])
    for index, source in enumerate(sources, start=1):
        heading = source.chunk_heading or "Untitled"
        text = truncate_text(source.chunk_text)
        metadata = render_source_metadata(source)
        lines.extend(
            [
                f"[S{index}] {source.document_title} / {heading}",
                f"Metadata: {metadata}",
                text,
                "",
            ]
        )

    lines.extend(
        [
            "Answer rules:",
            "- Answer only what the user asked.",
            "- Treat session evidence as authoritative for meeting existence, count, identity, date/time, status, and ordering.",
            "- Treat knowledge evidence as scoped by the resolved session IDs when session lookup metadata provides them.",
            "- If session evidence lists a meeting, do not say that meeting or month has no meeting because a report is missing.",
            "- Use knowledge evidence for meeting content, transcript, report, decisions, action items, risks, and discussion details.",
            "- If a meeting exists but no report/content evidence is available, distinguish the meeting's existence from missing report details.",
            "- If both evidence layers disagree, state the uncertainty instead of guessing.",
            "- For Korean questions, write the final answer in natural Korean only.",
            "- Cite only the evidence you actually used.",
            "- If the evidence does not support an answer, say the evidence is insufficient.",
        ]
    )
    return "\n".join(lines)
