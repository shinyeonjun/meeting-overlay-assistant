/**
 * 이벤트 컨트롤러
 *
 * - 이벤트 목록 새로고침
 * - quick action(확정/종료/삭제)
 * - 간단 수정(prompt 기반)
 */

import { elements } from "../dom/elements.js";
import { deleteEvent, updateEvent } from "../services/api-client.js";
import { normalizeEventPayload } from "../services/payload-normalizers.js";
import { appState } from "../state/app-state.js";
import { findEventItem, removeEventItem, upsertEventItem } from "../state/events-store.js";
import { flashStatus, setStatus } from "./ui-controller.js";
import { refreshEventBoard, refreshOverview } from "./shared-rendering.js";

function buildEditPayload(eventItem) {
    const title = window.prompt("이벤트 제목", eventItem.title);
    if (title === null) {
        return null;
    }

    const assignee = window.prompt("담당자(비우려면 빈 문자열)", eventItem.assignee ?? "");
    if (assignee === null) {
        return null;
    }

    const dueDate = window.prompt("기한(YYYY-MM-DD, 비우려면 빈 문자열)", eventItem.dueDate ?? "");
    if (dueDate === null) {
        return null;
    }

    return {
        title: title.trim() || eventItem.title,
        assignee: assignee.trim() || null,
        due_date: dueDate.trim() || null,
    };
}

async function handleEventAction(eventId, action) {
    if (!appState.session.id) {
        flashStatus(elements.sessionStatus, "세션 필요", "error");
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
        } else if (action === "confirm") {
            const updated = normalizeEventPayload(
                await updateEvent(appState.session.id, eventId, { state: "confirmed" }),
            );
            upsertEventItem(appState, updated);
        } else if (action === "close") {
            const updated = normalizeEventPayload(
                await updateEvent(appState.session.id, eventId, { state: "closed" }),
            );
            upsertEventItem(appState, updated);
        } else if (action === "edit") {
            const payload = buildEditPayload(current);
            if (!payload) {
                return;
            }
            const updated = normalizeEventPayload(
                await updateEvent(appState.session.id, eventId, payload),
            );
            upsertEventItem(appState, updated);
        }

        await refreshOverview();
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
}

export async function handleRefreshEvents() {
    if (!appState.session.id) {
        flashStatus(elements.sessionStatus, "세션 필요", "error");
        return;
    }

    setStatus(elements.sessionStatus, "이벤트 동기화 중", "idle");
    await refreshEventBoard();
    setStatus(elements.sessionStatus, "이벤트 동기화 완료", "live");
}
