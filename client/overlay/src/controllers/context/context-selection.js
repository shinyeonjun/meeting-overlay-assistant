/** 오버레이에서 컨텍스트 흐름의 context selection 제어를 담당한다. */
import { appState } from "../../state/app-state.js";
import {
    setSelectedAccountId,
    setSelectedContactId,
    setSelectedThreadId,
} from "../../state/context-store.js";

export function getSelectedMeetingContextRequest() {
    return {
        accountId: appState.context.selectedAccountId || null,
        contactId: appState.context.selectedContactId || null,
        contextThreadId: appState.context.selectedThreadId || null,
    };
}

export function getSelectedMeetingContextFilters() {
    return {
        accountId: appState.context.selectedAccountId || null,
        contactId: appState.context.selectedContactId || null,
        contextThreadId: appState.context.selectedThreadId || null,
    };
}

export function getSelectedMeetingContextSummary() {
    const selectedAccount = findAccountById(appState.context.selectedAccountId);
    const selectedContact = findContactById(appState.context.selectedContactId);
    const selectedThread = findThreadById(appState.context.selectedThreadId);

    return {
        hasSelection: Boolean(selectedAccount || selectedContact || selectedThread),
        accountLabel: selectedAccount?.name ?? "",
        contactLabel: selectedContact?.name ?? "",
        threadLabel: selectedThread?.title ?? "",
    };
}

export function clearMeetingContextSelection() {
    setSelectedAccountId(appState, "");
    setSelectedContactId(appState, "");
    setSelectedThreadId(appState, "");
}

export function reconcileSelections() {
    if (!findAccountById(appState.context.selectedAccountId)) {
        setSelectedAccountId(appState, "");
    }
    if (!findContactById(appState.context.selectedContactId)) {
        setSelectedContactId(appState, "");
    }
    if (!findThreadById(appState.context.selectedThreadId)) {
        setSelectedThreadId(appState, "");
    }

    const selectedContact = findContactById(appState.context.selectedContactId);
    if (selectedContact?.accountId && !appState.context.selectedAccountId) {
        setSelectedAccountId(appState, selectedContact.accountId);
    }

    const selectedThread = findThreadById(appState.context.selectedThreadId);
    if (selectedThread?.accountId) {
        setSelectedAccountId(appState, selectedThread.accountId);
    }
    if (selectedThread?.contactId) {
        setSelectedContactId(appState, selectedThread.contactId);
    }

    if (selectedThread && !isThreadCompatible(selectedThread)) {
        setSelectedThreadId(appState, "");
    }
}

export function getVisibleContacts() {
    if (!appState.context.selectedAccountId) {
        return appState.context.contacts;
    }
    return appState.context.contacts.filter(
        (item) => item.accountId === appState.context.selectedAccountId,
    );
}

export function getVisibleThreads() {
    return appState.context.threads.filter((item) => isThreadCompatible(item));
}

export function isThreadCompatible(item) {
    if (appState.context.selectedContactId) {
        if (item.contactId === appState.context.selectedContactId) {
            return true;
        }
        return !item.contactId && (
            !appState.context.selectedAccountId
            || item.accountId === appState.context.selectedAccountId
        );
    }

    if (appState.context.selectedAccountId) {
        return item.accountId === appState.context.selectedAccountId;
    }

    return true;
}

export function findAccountById(accountId) {
    if (!accountId) {
        return null;
    }
    return appState.context.accounts.find((item) => item.id === accountId) ?? null;
}

export function findContactById(contactId) {
    if (!contactId) {
        return null;
    }
    return appState.context.contacts.find((item) => item.id === contactId) ?? null;
}

export function findThreadById(contextThreadId) {
    if (!contextThreadId) {
        return null;
    }
    return appState.context.threads.find((item) => item.id === contextThreadId) ?? null;
}
