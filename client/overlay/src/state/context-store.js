export function applyMeetingContextSnapshot(state, { accounts, contacts, threads }) {
    state.context.accounts = accounts;
    state.context.contacts = contacts;
    state.context.threads = threads;
    state.context.lastLoadedAt = Date.now();
}

export function resetMeetingContextState(state) {
    state.context.accounts = [];
    state.context.contacts = [];
    state.context.threads = [];
    state.context.selectedAccountId = "";
    state.context.selectedContactId = "";
    state.context.selectedThreadId = "";
    state.context.loading = false;
    state.context.errorMessage = "";
    state.context.lastLoadedAt = null;
}

export function setMeetingContextLoading(state, loading) {
    state.context.loading = loading;
}

export function setMeetingContextError(state, message) {
    state.context.errorMessage = message ?? "";
}

export function setSelectedAccountId(state, accountId) {
    state.context.selectedAccountId = accountId ?? "";
}

export function setSelectedContactId(state, contactId) {
    state.context.selectedContactId = contactId ?? "";
}

export function setSelectedThreadId(state, contextThreadId) {
    state.context.selectedThreadId = contextThreadId ?? "";
}
