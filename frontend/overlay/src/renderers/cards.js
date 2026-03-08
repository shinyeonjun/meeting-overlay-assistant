function buildEmptyCard(text) {
    const element = document.createElement("div");
    element.className = "event-empty";
    element.textContent = text;
    return element;
}

function fillSpeaker(element, speakerLabel, fallback = "SYSTEM") {
    element.textContent = speakerLabel || fallback;
}

function buildMetaLine(item) {
    const parts = [];
    if (item.assignee) {
        parts.push(`담당 ${item.assignee}`);
    }
    if (item.dueDate) {
        parts.push(`기한 ${item.dueDate}`);
    }
    if (item.inputSource) {
        parts.push(`소스 ${item.inputSource}`);
    }
    return parts.join(" · ");
}

function createActionButton(label, action, eventId, tone = "secondary") {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `event-action-btn ${tone}`;
    button.dataset.action = action;
    button.dataset.eventId = eventId;
    button.textContent = label;
    return button;
}

export function renderEventColumn({ container, countElement, template }, items) {
    countElement.textContent = String(items.length);
    container.replaceChildren();

    if (!items.length) {
        container.append(buildEmptyCard("아직 이벤트가 없습니다."));
        return;
    }

    for (const item of items) {
        const fragment = template.content.cloneNode(true);
        const speakerElement = fragment.querySelector(".event-speaker");
        const stateElement = fragment.querySelector(".event-state");
        const titleElement = fragment.querySelector(".event-title");
        const bodyElement = fragment.querySelector(".event-body");

        fillSpeaker(speakerElement, item.speaker_label, "LIVE");
        stateElement.textContent = item.state;
        titleElement.textContent = item.title;
        bodyElement.remove();

        container.append(fragment);
    }
}

export function renderSpeakerTranscript({ container, countElement, template }, items) {
    countElement.textContent = String(items.length);
    container.replaceChildren();

    if (!items.length) {
        container.append(buildEmptyCard("화자 전사 결과가 없습니다."));
        return;
    }

    for (const item of items) {
        const fragment = template.content.cloneNode(true);
        const speakerElement = fragment.querySelector(".event-speaker");
        const timeElement = fragment.querySelector(".event-time");
        const stateElement = fragment.querySelector(".event-state");
        const bodyElement = fragment.querySelector(".event-body");

        fillSpeaker(speakerElement, item.speaker_label);
        timeElement.textContent = `${item.start_ms}ms - ${item.end_ms}ms`;
        stateElement.textContent = `conf ${Number(item.confidence).toFixed(3)}`;
        bodyElement.textContent = item.text;

        container.append(fragment);
    }
}

export function renderSpeakerEvents({ container, countElement, template }, items) {
    countElement.textContent = String(items.length);
    container.replaceChildren();

    if (!items.length) {
        container.append(buildEmptyCard("화자-이벤트 연결 결과가 없습니다."));
        return;
    }

    for (const item of items) {
        const fragment = template.content.cloneNode(true);
        const speakerElement = fragment.querySelector(".event-speaker");
        const stateElement = fragment.querySelector(".event-state");
        const titleElement = fragment.querySelector(".event-title");
        const bodyElement = fragment.querySelector(".event-body");

        fillSpeaker(speakerElement, item.speaker_label);
        stateElement.textContent = `${item.event_type} / ${item.state}`;
        titleElement.textContent = item.title;
        bodyElement.remove();

        container.append(fragment);
    }
}

export function renderManagedEventColumn({ container, countElement, template }, items) {
    countElement.textContent = String(items.length);
    container.replaceChildren();

    if (!items.length) {
        container.append(buildEmptyCard("아직 이벤트가 없습니다."));
        return;
    }

    for (const item of items) {
        const fragment = template.content.cloneNode(true);
        const card = fragment.querySelector(".event-card");
        const speakerElement = fragment.querySelector(".event-speaker");
        const stateElement = fragment.querySelector(".event-state");
        const titleElement = fragment.querySelector(".event-title");
        const bodyElement = fragment.querySelector(".event-body");

        card.dataset.eventId = item.id;
        fillSpeaker(speakerElement, item.speakerLabel, "LIVE");
        stateElement.textContent = `${item.eventType} / ${item.state}`;
        titleElement.textContent = item.title;

        const detailLines = [item.evidenceText || item.body, buildMetaLine(item)].filter(Boolean);
        if (detailLines.length === 0) {
            bodyElement.remove();
        } else {
            bodyElement.textContent = detailLines.join("\n");
            bodyElement.classList.add("event-body--managed");
        }

        const actions = document.createElement("div");
        actions.className = "event-actions";
        actions.append(createActionButton("수정", "edit", item.id));
        actions.append(createActionButton("처리 완료", "complete", item.id));
        card.append(actions);

        container.append(fragment);
    }
}
