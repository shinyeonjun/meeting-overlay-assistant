"""Assistant query planning JSON schema."""

from __future__ import annotations

from typing import Any


QUERY_PLAN_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "search_query": {
            "type": "string",
            "description": "Concise retrieval query that preserves concrete nouns, dates, meeting names, and requested evidence.",
        },
        "answer_focus": {
            "type": "string",
            "description": "Short description of what the final answer should focus on.",
        },
        "retrieval_sources": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["knowledge", "sessions"],
            },
            "description": "Always include both sessions and knowledge; the runtime treats this as a unified evidence request.",
        },
        "target_dates": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Resolved YYYY-MM-DD dates based on the current KST context. Empty when not clear.",
        },
        "time_scope": {
            "type": "string",
            "description": "Brief description of the interpreted time scope. Empty when not relevant.",
        },
        "time_expression": {
            "type": "string",
            "description": "Original relative or explicit time expression from the user. Empty when absent.",
        },
        "resolved_time_range": {
            "type": "string",
            "description": "Resolved time range based on the current KST context. Empty when not clear.",
        },
        "session_scope": {
            "type": "string",
            "enum": [
                "",
                "latest",
                "previous",
                "recent_list",
                "date",
                "month",
                "title",
                "all",
            ],
            "description": "Structured meeting scope to resolve from the relational session tables before knowledge retrieval.",
        },
        "content_focuses": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "summary",
                    "decision",
                    "action_item",
                    "risk",
                    "question",
                    "discussion",
                    "transcript",
                    "metadata",
                ],
            },
            "description": "Content sections the answer needs after the target sessions are resolved.",
        },
        "requires_knowledge": {
            "type": "boolean",
            "description": "False for metadata-only questions such as latest meeting, meeting count, existence, date, or title.",
        },
        "needs_clarification": {
            "type": "boolean",
            "description": "Whether retrieval is impossible without more user input.",
        },
        "clarification_question": {
            "type": ["string", "null"],
            "description": "Short clarification question when needs_clarification is true.",
        },
        "confidence": {
            "type": "number",
            "description": "Planning confidence from 0 to 1.",
        },
    },
    "required": [
        "search_query",
        "answer_focus",
        "retrieval_sources",
        "target_dates",
        "time_scope",
        "time_expression",
        "resolved_time_range",
        "session_scope",
        "content_focuses",
        "requires_knowledge",
        "needs_clarification",
        "clarification_question",
        "confidence",
    ],
    "additionalProperties": False,
}
