/** 오버레이에서 공통 흐름의 events controller 제어를 담당한다. */
import { elements } from "../dom/elements.js";
import { transitionEvent, updateEvent } from "../services/api/events-api.js";
import { normalizeEventPayload } from "../services/payload-normalizers.js";
import { appState } from "../state/app-state.js";
import { findEventItem, upsertEventItem } from "../state/events-store.js";
import { renderEventBoard, refreshEventBoard } from "./events-board-controller.js";
import { refreshSessionOverview } from "./session/session-overview-controller.js";
import { flashStatus, setStatus } from "./ui-controller.js";

function resolveCompleteTarget(eventItem) {
    if (eventItem.eventType === "question") {
        return "answered";
    }
    if (eventItem.eventType === "risk") {
        return "resolved";
    }
    if (eventItem.eventType === "action_item" || eventItem.eventType === "decision") {
        return "closed";
    }
    return "closed";
}

function closeEventEditor() {
    appState.events.editingEventId = null;
    elements.eventEditor?.classList.add("hidden");
    if (elements.eventEditorTitle) {
        elements.eventEditorTitle.textContent = "이벤트 수정";
    }
    if (elements.eventEditTitle) {
        elements.eventEditTitle.value = "";
    }
}

function openEventEditor(eventItem) {
    appState.events.editingEventId = eventItem.id;
    if (elements.eventEditorTitle) {
        elements.eventEditorTitle.textContent = `${eventItem.eventType} 수정`;
    }
    if (elements.eventEditTitle) {
        elements.eventEditTitle.value = eventItem.title ?? "";
    }
    elements.eventEditor?.classList.remove("hidden");
}

async function saveEventEdit() {
    if (!appState.session.id) {
        flashStatus(elements.sessionStatus, "세션이 필요합니다.", "error");
        return;
    }

    const eventId = appState.events.editingEventId;
    if (!eventId) {
        return;
    }

    const current = findEventItem(appState, eventId);
    if (!current) {
        closeEventEditor();
        await refreshEventBoard();
        return;
    }

    try {
        setStatus(elements.sessionStatus, "이벤트 수정 저장 중", "idle");
        const updated = normalizeEventPayload(
            await updateEvent(appState.session.id, eventId, {
                title: elements.eventEditTitle?.value.trim() || current.title,
            }),
        );
        upsertEventItem(appState, updated);
        closeEventEditor();
        await refreshSessionOverview();
        renderEventBoard();
        setStatus(elements.sessionStatus, "이벤트 수정 완료", "live");
    } catch (error) {
        console.error(error);
        flashStatus(elements.sessionStatus, "이벤트 수정 실패", "error");
    }
}

async function handleEventAction(eventId, action) {
    if (!appState.session.id) {
        flashStatus(elements.sessionStatus, "세션이 필요합니다.", "error");
        return;
    }

    const current = findEventItem(appState, eventId);
    if (!current) {
        await refreshEventBoard();
        return;
    }

    if (action === "edit") {
        openEventEditor(current);
        return;
    }

    if (action !== "complete") {
        return;
    }

    try {
        setStatus(elements.sessionStatus, "이벤트 반영 중", "idle");
        const updated = normalizeEventPayload(
            await transitionEvent(appState.session.id, eventId, {
                target_state: resolveCompleteTarget(current),
            }),
        );
        upsertEventItem(appState, updated);
        if (appState.events.editingEventId === eventId) {
            closeEventEditor();
        }
        await refreshSessionOverview();
        renderEventBoard();
        setStatus(elements.sessionStatus, "이벤트 반영 완료", "live");
    } catch (error) {
        console.error(error);
        flashStatus(elements.sessionStatus, "이벤트 반영 실패", "error");
    }
}

export function setupEventActionDelegation() {
    const containers = [
        elements.questionsList,
        elements.decisionsList,
        elements.actionsList,
        elements.risksList,
    ];

    for (const container of containers) {
        container?.addEventListener("click", (event) => {
            const button = event.target.closest(".event-action-btn");
            if (!button) {
                return;
            }
            void handleEventAction(button.dataset.eventId, button.dataset.action);
        });
    }

    elements.saveEventEditButton?.addEventListener("click", () => {
        void saveEventEdit();
    });
    elements.cancelEventEditButton?.addEventListener("click", () => {
        closeEventEditor();
    });
}

export async function handleRefreshEvents() {
    if (!appState.session.id) {
        flashStatus(elements.sessionStatus, "세션이 필요합니다.", "error");
        return;
    }

    setStatus(elements.sessionStatus, "이벤트 불러오는 중", "idle");
    await refreshEventBoard();
    setStatus(elements.sessionStatus, "이벤트 불러오기 완료", "live");
}
