function createEmptyGroupedEvents() {
    return {
        questions: [],
        decisions: [],
        actionItems: [],
        risks: [],
    };
}

function resolveGroupKey(eventType) {
    if (eventType === "question") {
        return "questions";
    }
    if (eventType === "decision") {
        return "decisions";
    }
    if (eventType === "action_item") {
        return "actionItems";
    }
    if (eventType === "risk") {
        return "risks";
    }
    return null;
}

function rebuildGroupedEvents(items) {
    const grouped = createEmptyGroupedEvents();
    for (const item of items) {
        const key = resolveGroupKey(item.eventType);
        if (!key) {
            continue;
        }
        grouped[key].push(item);
    }
    return grouped;
}

export function applyEventList(state, items) {
    state.events.items = items;
    state.events.grouped = rebuildGroupedEvents(items);
    state.events.selectedIds = new Set(
        [...state.events.selectedIds].filter((eventId) =>
            items.some((item) => item.id === eventId),
        ),
    );
    state.events.lastLoadedAt = Date.now();
}

export function upsertEventItem(state, item) {
    const nextItems = [...state.events.items];
    const index = nextItems.findIndex((current) => current.id === item.id);
    if (index >= 0) {
        nextItems[index] = item;
    } else {
        nextItems.unshift(item);
    }
    applyEventList(state, nextItems);
}

export function removeEventItem(state, eventId) {
    applyEventList(
        state,
        state.events.items.filter((item) => item.id !== eventId),
    );
}

export function findEventItem(state, eventId) {
    return state.events.items.find((item) => item.id === eventId) ?? null;
}

export function toggleEventSelection(state, eventId) {
    if (state.events.selectedIds.has(eventId)) {
        state.events.selectedIds.delete(eventId);
        return false;
    }
    state.events.selectedIds.add(eventId);
    return true;
}

export function clearEventSelection(state) {
    state.events.selectedIds.clear();
}
