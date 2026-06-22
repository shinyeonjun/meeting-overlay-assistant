"""Assistant query-planning prompts."""

from __future__ import annotations


def build_planner_system_prompt() -> str:
    """Build the system prompt for query planning."""

    return (
        "You are the CAPS meeting-data query planner. Do not answer the user. "
        "Return only JSON that preserves the user's intent for retrieval. "
        "Do not choose between data sources; the system will retrieve both session metadata "
        "and meeting knowledge."
    )


def build_planner_prompt(
    *,
    query: str,
    requested_source_types: tuple[str, ...],
    time_context_text: str,
    conversation_history_text: str = "",
) -> str:
    """Build the user prompt that turns a user question into a retrieval plan."""

    requested = ", ".join(requested_source_types) if requested_source_types else "none"
    lines = [
        "Convert the user question into a CAPS retrieval plan.",
        "",
        "Current time context:",
        time_context_text,
        "",
    ]
    if conversation_history_text:
        lines.extend(
            [
                "Recent conversation:",
                conversation_history_text,
                "",
            ]
        )
    lines.extend(
        [
            f"Question: {query}",
            f"Requested knowledge source-type filter: {requested}",
            "",
            "Available evidence layers:",
            "- sessions: structured meeting metadata such as title, date/time, status, input source, participants.",
            "- knowledge: indexed meeting notes, transcripts, reports, decisions, action items, risks, and discussion text.",
            "",
            "Planning rules:",
            "- Do not answer the question.",
            "- Preserve concrete nouns, meeting names, people, dates, and requested evidence in search_query.",
            "- Resolve explicit or relative dates against the current time context when possible.",
            "- Put resolved YYYY-MM-DD dates in target_dates only when the date is clear.",
            "- Use time_scope, time_expression, and resolved_time_range only as retrieval metadata.",
            "- Set session_scope to latest for 'most recent/latest/last meeting' questions that ask for one meeting.",
            "- Set session_scope to recent_list, month, date, title, or all when the user asks for a list, count, existence, specific month/date/title, or broad search.",
            "- Set requires_knowledge=false for meeting identity, existence, count, date/time, title, or status questions.",
            "- Set requires_knowledge=true when the user asks what was discussed, decided, assigned, risky, asked, or said.",
            "- Put requested sections in content_focuses, such as decision, action_item, risk, question, summary, discussion, transcript, or metadata.",
            "- Keep retrieval_sources as both sessions and knowledge.",
            "- Set needs_clarification only when retrieval would be impossible without more user input.",
            "- Never invent meetings, dates, decisions, or source content.",
        ]
    )
    return "\n".join(lines)
