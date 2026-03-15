import { elements } from "../../dom/elements.js";
import { appState } from "../../state/app-state.js";
import {
    getVisibleContacts,
    getVisibleThreads,
} from "./context-selection.js";

export function renderMeetingContextControls() {
    renderSelect(
        elements.sessionAccount,
        appState.context.accounts.map((item) => ({
            value: item.id,
            label: item.name,
        })),
        appState.context.selectedAccountId,
        "회사 선택 안 함",
    );

    renderSelect(
        elements.sessionContact,
        getVisibleContacts().map((item) => ({
            value: item.id,
            label: item.jobTitle ? `${item.name} / ${item.jobTitle}` : item.name,
        })),
        appState.context.selectedContactId,
        "상대방 선택 안 함",
    );

    renderSelect(
        elements.sessionThread,
        getVisibleThreads().map((item) => ({
            value: item.id,
            label: item.title,
        })),
        appState.context.selectedThreadId,
        "업무 흐름 선택 안 함",
    );

    const disabled = appState.context.loading;
    if (elements.sessionAccount) {
        elements.sessionAccount.disabled = disabled;
    }
    if (elements.sessionContact) {
        elements.sessionContact.disabled = disabled;
    }
    if (elements.sessionThread) {
        elements.sessionThread.disabled = disabled;
    }
    if (elements.sessionContextRefreshButton) {
        elements.sessionContextRefreshButton.disabled = disabled;
    }
    if (elements.sessionContextStatus) {
        elements.sessionContextStatus.textContent = resolveStatusText();
        elements.sessionContextStatus.classList.toggle(
            "error-text",
            Boolean(appState.context.errorMessage),
        );
    }
}

function renderSelect(element, items, selectedValue, emptyLabel) {
    if (!element) {
        return;
    }

    const options = [
        `<option value="">${escapeHtml(emptyLabel)}</option>`,
        ...items.map(
            (item) => `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`,
        ),
    ];
    element.innerHTML = options.join("");
    element.value = selectedValue || "";
}

function resolveStatusText() {
    if (appState.context.errorMessage) {
        return appState.context.errorMessage;
    }

    if (appState.context.loading) {
        return "회의 맥락 목록을 불러오는 중입니다.";
    }

    return `회사 ${appState.context.accounts.length}개 / 상대방 ${appState.context.contacts.length}명 / 업무 흐름 ${appState.context.threads.length}개`;
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}
