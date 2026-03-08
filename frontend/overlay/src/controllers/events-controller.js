import { elements } from "../dom/elements.js";
import {
    bulkTransitionEvents,
    deleteEvent,
    transitionEvent,
    updateEvent,
} from "../services/api-client.js";
import { normalizeEventPayload } from "../services/payload-normalizers.js";
import { appState } from "../state/app-state.js";
import {
    clearEventSelection,
    findEventItem,
    removeEventItem,
    toggleEventSelection,
    upsertEventItem,
} from "../state/events-store.js";
import { refreshEventBoard, refreshOverview, renderEventToolbar, renderOverviewColumns } from "./shared-rendering.js";
import { flashStatus, setStatus } from "./ui-controller.js";

function buildEditPayload(eventItem) {
    const title = window.prompt("이벤트 제목", eventItem.title);
    if (title === null) {
        return null;
    }

    const assignee = window.prompt("담당자, 비우려면 빈 문자열", eventItem.assignee ?? "");
    if (assignee === null) {
        return null;
    }

    const dueDate = window.prompt("기한(YYYY-MM-DD), 비우려면 빈 문자열", eventItem.dueDate ?? "");
    if (dueDate === null) {
        return null;
    }

    return {
        title: title.trim() || eventItem.title,
        assignee: assignee.trim() || null,
        due_date: dueDate.trim() || null,
    };
}

function resolveTransitionTarget(action) {
    if (action === "confirm") {
        return "confirmed";
    }
    if (action === "update-state") {
        return "updated";
    }
    if (action === "answer") {
        return "answered";
    }
    if (action === "activate") {
        return "active";
    }
    if (action === "monitor") {
        return "monitoring";
    }
    if (action === "resolve") {
        return "resolved";
    }
    if (action === "close") {
        return "closed";
    }
    return null;
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

    try {
        setStatus(elements.sessionStatus, "이벤트 반영 중", "idle");

        if (action === "delete") {
            const confirmed = window.confirm("이 이벤트를 삭제하시겠습니까?");
            if (!confirmed) {
                return;
            }
            await deleteEvent(appState.session.id, eventId);
            removeEventItem(appState, eventId);
        } else if (action === "edit") {
            const payload = buildEditPayload(current);
            if (!payload) {
                return;
            }
            const updated = normalizeEventPayload(
                await updateEvent(appState.session.id, eventId, payload),
            );
            upsertEventItem(appState, updated);
        } else {
            const targetState = resolveTransitionTarget(action);
            if (!targetState) {
                return;
            }
            const updated = normalizeEventPayload(
                await transitionEvent(appState.session.id, eventId, { target_state: targetState }),
            );
            upsertEventItem(appState, updated);
        }

        await refreshOverview();
        renderOverviewColumns();
        setStatus(elements.sessionStatus, "이벤트 반영 완료", "live");
    } catch (error) {
        console.error(error);
        flashStatus(elements.sessionStatus, "이벤트 반영 실패", "error");
    }
}

async function handleBulkAction(targetState) {
    if (!appState.session.id) {
        flashStatus(elements.sessionStatus, "세션이 필요합니다.", "error");
        return;
    }

    const eventIds = [...appState.events.selectedIds];
    if (!eventIds.length) {
        flashStatus(elements.sessionStatus, "선택된 이벤트가 없습니다.", "error");
        return;
    }

    try {
        setStatus(elements.sessionStatus, "이벤트 일괄 반영 중", "idle");
        const response = await bulkTransitionEvents(appState.session.id, {
            event_ids: eventIds,
            target_state: targetState,
        });

        for (const item of response.items ?? []) {
            upsertEventItem(appState, normalizeEventPayload(item));
        }

        clearEventSelection(appState);
        await refreshOverview();
        renderOverviewColumns();
        setStatus(elements.sessionStatus, "이벤트 일괄 반영 완료", "live");
    } catch (error) {
        console.error(error);
        flashStatus(elements.sessionStatus, "이벤트 일괄 반영 실패", "error");
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

        container?.addEventListener("change", (event) => {
            const checkbox = event.target.closest(".event-select-checkbox");
            if (!checkbox) {
                return;
            }
            toggleEventSelection(appState, checkbox.dataset.eventId);
            renderEventToolbar();
            renderOverviewColumns();
        });
    }

    elements.bulkConfirmEventsButton?.addEventListener("click", () => {
        void handleBulkAction("confirmed");
    });
    elements.bulkCloseEventsButton?.addEventListener("click", () => {
        void handleBulkAction("closed");
    });
    elements.clearSelectedEventsButton?.addEventListener("click", () => {
        clearEventSelection(appState);
        renderOverviewColumns();
        renderEventToolbar();
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
