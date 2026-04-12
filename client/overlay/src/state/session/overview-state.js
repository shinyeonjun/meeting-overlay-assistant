/** 오버레이의 세션 상태를 관리한다. */
export function createEmptyOverviewBuckets() {
    return {
        questions: [],
        decisions: [],
        actionItems: [],
        risks: [],
    };
}

export function createNormalizedOverviewEvent(item) {
    return {
        id: item.id,
        title: item.title,
        state: item.state,
        speaker_label: item.speaker_label ?? null,
    };
}

export function resolveOverviewBucket(overview, eventType) {
    if (eventType === "question") {
        return overview.questions;
    }
    if (eventType === "decision") {
        return overview.decisions;
    }
    if (eventType === "action_item") {
        return overview.actionItems;
    }
    if (eventType === "risk") {
        return overview.risks;
    }
    return null;
}

export function mergeOverviewBuckets(baseOverview, liveOverview) {
    return {
        questions: mergeBucket(baseOverview.questions, liveOverview.questions),
        decisions: mergeBucket(baseOverview.decisions, liveOverview.decisions),
        actionItems: mergeBucket(baseOverview.actionItems, liveOverview.actionItems),
        risks: mergeBucket(baseOverview.risks, liveOverview.risks),
    };
}

function mergeBucket(baseItems = [], liveItems = []) {
    const merged = [];
    const seen = new Set();

    for (const item of liveItems) {
        const key = item.id ?? `${item.title}:${item.state}`;
        if (seen.has(key)) {
            continue;
        }
        seen.add(key);
        merged.push(item);
    }

    for (const item of baseItems) {
        const key = item.id ?? `${item.title}:${item.state}`;
        if (seen.has(key)) {
            continue;
        }
        seen.add(key);
        merged.push(item);
    }

    return merged;
}
