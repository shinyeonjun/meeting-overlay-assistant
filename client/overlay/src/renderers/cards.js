/** 오버레이 런타임의 cards 모듈이다. */
function buildEmptyCard(text) {
    const element = document.createElement("div");
    element.className = "event-empty";
    element.textContent = text;
    return element;
}

function fillSpeaker(element, speakerLabel, fallback = "SYSTEM") {
    element.textContent = speakerLabel || fallback;
}

function formatEventTypeLabel(eventType) {
    if (eventType === "topic") {
        return "주제";
    }
    switch (eventType) {
        case "question":
            return "질문";
        case "decision":
            return "결정 사항";
        case "action_item":
            return "액션 아이템";
        case "risk":
            return "리스크";
        default:
            return "";
    }
}

function buildMetaLine(item) {
    const parts = [];
    if (item.state) {
        parts.push(`상태 ${item.state}`);
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
        stateElement.remove();
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
        const eventTypeLabel = formatEventTypeLabel(item.event_type);
        if (eventTypeLabel) {
            stateElement.textContent = eventTypeLabel;
        } else {
            stateElement.remove();
        }
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
        stateElement.remove();
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
