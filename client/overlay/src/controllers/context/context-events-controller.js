/** 오버레이에서 컨텍스트 흐름의 context events controller 제어를 담당한다. */
import { elements } from "../../dom/elements.js";
import { appState } from "../../state/app-state.js";
import {
    setSelectedAccountId,
    setSelectedContactId,
    setSelectedThreadId,
} from "../../state/context-store.js";
import {
    findContactById,
    findThreadById,
    isThreadCompatible,
} from "./context-selection.js";
import { renderMeetingContextControls } from "./context-renderer.js";
import {
    refreshMeetingContextOptions,
} from "./context-refresh-controller.js";

let contextEventsBound = false;

export function setupContextControls() {
    if (contextEventsBound) {
        return;
    }

    elements.sessionAccount?.addEventListener("change", handleAccountChange);
    elements.sessionContact?.addEventListener("change", handleContactChange);
    elements.sessionThread?.addEventListener("change", handleThreadChange);
    elements.sessionContextRefreshButton?.addEventListener("click", () => {
        void refreshMeetingContextOptions();
    });

    contextEventsBound = true;
    renderMeetingContextControls();
}

function handleAccountChange() {
    setSelectedAccountId(appState, elements.sessionAccount?.value ?? "");

    const selectedContact = findContactById(appState.context.selectedContactId);
    if (
        selectedContact
        && appState.context.selectedAccountId
        && selectedContact.accountId !== appState.context.selectedAccountId
    ) {
        setSelectedContactId(appState, "");
    }

    const selectedThread = findThreadById(appState.context.selectedThreadId);
    if (selectedThread && !isThreadCompatible(selectedThread)) {
        setSelectedThreadId(appState, "");
    }

    renderMeetingContextControls();
}

function handleContactChange() {
    setSelectedContactId(appState, elements.sessionContact?.value ?? "");

    const selectedContact = findContactById(appState.context.selectedContactId);
    if (selectedContact?.accountId) {
        setSelectedAccountId(appState, selectedContact.accountId);
    }

    const selectedThread = findThreadById(appState.context.selectedThreadId);
    if (selectedThread && !isThreadCompatible(selectedThread)) {
        setSelectedThreadId(appState, "");
    }

    renderMeetingContextControls();
}

function handleThreadChange() {
    setSelectedThreadId(appState, elements.sessionThread?.value ?? "");

    const selectedThread = findThreadById(appState.context.selectedThreadId);
    if (selectedThread?.accountId) {
        setSelectedAccountId(appState, selectedThread.accountId);
    }
    if (selectedThread?.contactId) {
        setSelectedContactId(appState, selectedThread.contactId);
    }

    renderMeetingContextControls();
}
