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

function createSelectionToggle(eventId, checked) {
    const label = document.createElement("label");
    label.className = "event-select-toggle";

    const input = document.createElement("input");
    input.type = "checkbox";
    input.className = "event-select-checkbox";
    input.dataset.eventId = eventId;
    input.checked = checked;

    const text = document.createElement("span");
    text.textContent = "선택";

    label.append(input, text);
    return label;
}

function resolvePrimaryAction(item) {
    if (item.eventType === "question") {
        if (item.state === "open") {
            return { label: "답변 처리", action: "answer" };
        }
        return null;
    }

    if (item.eventType === "risk") {
        if (item.state === "open") {
            return { label: "활성화", action: "activate" };
        }
        if (item.state === "active") {
            return { label: "모니터링", action: "monitor" };
        }
        if (item.state === "monitoring") {
            return { label: "해결", action: "resolve" };
        }
        return null;
    }

    if (item.state !== "confirmed") {
        return { label: "확정", action: "confirm" };
    }

    if (item.state !== "updated") {
        return { label: "수정 반영", action: "update-state" };
    }

    return null;
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

export function renderManagedEventColumn({ container, countElement, template, selectedIds }, items) {
    countElement.textContent = String(items.length);
    container.replaceChildren();

    if (!items.length) {
        container.append(buildEmptyCard("아직 이벤트가 없습니다."));
        return;
    }

    for (const item of items) {
        const fragment = template.content.cloneNode(true);
        const card = fragment.querySelector(".event-card");
        const top = fragment.querySelector(".event-card-top");
        const speakerElement = fragment.querySelector(".event-speaker");
        const stateElement = fragment.querySelector(".event-state");
        const titleElement = fragment.querySelector(".event-title");
        const bodyElement = fragment.querySelector(".event-body");
        const isSelected = selectedIds?.has(item.id) ?? false;

        card.dataset.eventId = item.id;
        card.classList.toggle("selected", isSelected);
        top.prepend(createSelectionToggle(item.id, isSelected));
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

        const primaryAction = resolvePrimaryAction(item);
        if (primaryAction) {
            actions.append(createActionButton(primaryAction.label, primaryAction.action, item.id));
        }

        if (item.state !== "closed") {
            actions.append(createActionButton("종료", "close", item.id));
        }

        actions.append(createActionButton("삭제", "delete", item.id, "danger"));
        card.append(actions);
        container.append(fragment);
    }
}
