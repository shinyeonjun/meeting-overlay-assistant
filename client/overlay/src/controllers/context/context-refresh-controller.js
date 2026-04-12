/** 오버레이에서 컨텍스트 흐름의 context refresh controller 제어를 담당한다. */
import {
    listAccounts,
    listContacts,
    listContextThreads,
} from "../../services/api/context-api.js";
import {
    normalizeAccountListPayload,
    normalizeContactListPayload,
    normalizeContextThreadListPayload,
} from "../../services/payload-normalizers.js";
import { appState } from "../../state/app-state.js";
import {
    applyMeetingContextSnapshot,
    resetMeetingContextState,
    setMeetingContextError,
    setMeetingContextLoading,
} from "../../state/context-store.js";
import {
    clearMeetingContextSelection,
    reconcileSelections,
} from "./context-selection.js";
import { renderMeetingContextControls } from "./context-renderer.js";

export async function refreshMeetingContextOptions() {
    if (!canRenderContextControls()) {
        return;
    }

    setMeetingContextLoading(appState, true);
    setMeetingContextError(appState, "");
    renderMeetingContextControls();

    try {
        const [accountsPayload, contactsPayload, threadsPayload] = await Promise.all([
            listAccounts({ limit: 100 }),
            listContacts({ limit: 100 }),
            listContextThreads({ limit: 100 }),
        ]);

        applyMeetingContextSnapshot(appState, {
            accounts: normalizeAccountListPayload(accountsPayload),
            contacts: normalizeContactListPayload(contactsPayload),
            threads: normalizeContextThreadListPayload(threadsPayload),
        });
        reconcileSelections();
    } catch (error) {
        console.error("[CAPS] 회의 맥락 목록 조회 실패:", error);
        setMeetingContextError(
            appState,
            "회사, 상대방, 업무 흐름 목록을 불러오지 못했습니다. 서버 연결과 권한을 확인해 주세요.",
        );
    }

    setMeetingContextLoading(appState, false);
    renderMeetingContextControls();
}

export function resetMeetingContextControls() {
    resetMeetingContextState(appState);
    renderMeetingContextControls();
}

export function clearMeetingContextControls() {
    clearMeetingContextSelection();
    renderMeetingContextControls();
}

function canRenderContextControls() {
    return Boolean(
        document.querySelector("#session-account")
        && document.querySelector("#session-contact")
        && document.querySelector("#session-thread"),
    );
}
