"""추론 스케줄러 ready queue helper."""

from __future__ import annotations

from collections import deque


def enqueue_ready_context(
    *,
    context_id: str,
    preferred_kind: str,
    priority: str,
    ready_queue_memberships: dict[str, set[str]],
    high_final_ready_ids: deque[str],
    preview_ready_ids: deque[str],
    normal_final_ready_ids: deque[str],
) -> None:
    """context를 kind별 ready queue에 등록한다."""

    queue_name = resolve_queue_name(preferred_kind=preferred_kind, priority=priority)
    memberships = ready_queue_memberships.setdefault(context_id, set())
    if queue_name in memberships:
        return
    memberships.add(queue_name)
    if queue_name == "high_final":
        high_final_ready_ids.append(context_id)
        return
    if queue_name == "preview":
        preview_ready_ids.append(context_id)
        return
    normal_final_ready_ids.append(context_id)


def discard_ready_context(
    context_id: str,
    *,
    ready_queue_memberships: dict[str, set[str]],
    high_final_ready_ids: deque[str],
    preview_ready_ids: deque[str],
    normal_final_ready_ids: deque[str],
) -> tuple[deque[str], deque[str], deque[str]]:
    """context를 모든 ready queue에서 제거한다."""

    ready_queue_memberships.pop(context_id, None)
    return (
        deque(
            queued_context_id
            for queued_context_id in high_final_ready_ids
            if queued_context_id != context_id
        ),
        deque(
            queued_context_id
            for queued_context_id in preview_ready_ids
            if queued_context_id != context_id
        ),
        deque(
            queued_context_id
            for queued_context_id in normal_final_ready_ids
            if queued_context_id != context_id
        ),
    )


def pop_next_ready_context(
    *,
    registry,
    ready_queue_memberships: dict[str, set[str]],
    high_final_ready_ids: deque[str],
    preview_ready_ids: deque[str],
    normal_final_ready_ids: deque[str],
) -> tuple[object, str] | None:
    """우선순위에 따라 다음 ready context를 꺼낸다."""

    for queue_name, ready_ids in (
        ("high_final", high_final_ready_ids),
        ("preview", preview_ready_ids),
        ("normal_final", normal_final_ready_ids),
    ):
        context = _pop_ready_context(
            registry=registry,
            ready_ids=ready_ids,
            expected_queue_name=queue_name,
            ready_queue_memberships=ready_queue_memberships,
        )
        if context is not None:
            return context
    return None


def _pop_ready_context(
    *,
    registry,
    ready_ids: deque[str],
    expected_queue_name: str,
    ready_queue_memberships: dict[str, set[str]],
) -> tuple[object, str] | None:
    while ready_ids:
        context_id = ready_ids.popleft()
        memberships = ready_queue_memberships.get(context_id)
        if memberships is None or expected_queue_name not in memberships:
            continue
        memberships.remove(expected_queue_name)
        if not memberships:
            ready_queue_memberships.pop(context_id, None)

        context = registry.get_context(context_id)
        if context is None:
            continue

        preferred_kind = "preview" if expected_queue_name == "preview" else "final"
        return context, preferred_kind
    return None


def resolve_queue_name(*, preferred_kind: str, priority: str) -> str:
    """job kind와 priority에 맞는 queue 이름을 계산한다."""

    if preferred_kind == "preview":
        return "preview"
    if priority == "high":
        return "high_final"
    return "normal_final"
