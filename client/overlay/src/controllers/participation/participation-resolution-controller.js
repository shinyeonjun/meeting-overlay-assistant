import { elements } from "../../dom/elements.js";
import {
    createContactFromSessionParticipant,
    fetchSessionParticipantFollowups,
    fetchSessionParticipation,
    linkContactForSessionParticipant,
} from "../../services/api/participation-api.js";
import {
    normalizeParticipantFollowupListPayload,
    normalizeSessionParticipationPayload,
    normalizeSessionPayload,
} from "../../services/payload-normalizers.js";
import { appState } from "../../state/app-state.js";
import {
    setSession,
    setSessionParticipation,
    setSessionParticipantFollowups,
} from "../../state/session/meeting-session-store.js";
import { refreshMeetingContextOptions } from "../context-controller.js";
import { refreshHistorySnapshot } from "../history-controller.js";
import { flashStatus } from "../ui-controller.js";
import { renderSessionSummary } from "../session/session-summary-renderer.js";

let participantCandidateEventsBound = false;

export function bindParticipantCandidateEvents() {
    if (participantCandidateEventsBound || !elements.sessionParticipantCandidatesList) {
        return;
    }

    elements.sessionParticipantCandidatesList.addEventListener("click", (event) => {
        const createButton = event.target.closest("[data-participant-contact-name]");
        if (createButton) {
            const participantName = createButton.dataset.participantContactName;
            if (participantName) {
                void handleCreateParticipantContact(participantName);
            }
            return;
        }

        const linkButton = event.target.closest("[data-participant-link-name][data-participant-link-contact-id]");
        if (!linkButton) {
            return;
        }

        const participantName = linkButton.dataset.participantLinkName;
        const contactId = linkButton.dataset.participantLinkContactId;
        if (!participantName || !contactId) {
            return;
        }

        void handleLinkParticipantContact(participantName, contactId);
    });

    participantCandidateEventsBound = true;
}

export function parseSessionParticipants(participantsText) {
    const normalized = [];
    const seen = new Set();
    for (const rawValue of participantsText.split(/[\n,;]+/)) {
        const value = rawValue.trim();
        if (!value || seen.has(value)) {
            continue;
        }
        normalized.push(value);
        seen.add(value);
    }
    return normalized;
}

export function renderParticipantCandidates() {
    if (
        !elements.sessionParticipantCandidatesPanel
        || !elements.sessionParticipantCandidatesList
        || !elements.sessionParticipantCandidatesStatus
    ) {
        return;
    }

    const candidates = appState.session.participantCandidates ?? [];
    if (!appState.session.id || !candidates.length) {
        elements.sessionParticipantCandidatesPanel.classList.add("hidden");
        elements.sessionParticipantCandidatesList.replaceChildren();
        elements.sessionParticipantCandidatesStatus.textContent = "아직 확인할 참여자 후보가 없습니다.";
        return;
    }

    elements.sessionParticipantCandidatesPanel.classList.remove("hidden");
    elements.sessionParticipantCandidatesList.replaceChildren();

    const summary = appState.session.participationSummary ?? null;
    const unresolvedCount = summary?.unmatchedCount ?? candidates.filter((item) => item.resolutionStatus === "unmatched").length;
    const ambiguousCount = summary?.ambiguousCount ?? candidates.filter((item) => item.resolutionStatus === "ambiguous").length;
    elements.sessionParticipantCandidatesStatus.textContent = [
        unresolvedCount ? `새 contact 후보 ${unresolvedCount}명` : null,
        ambiguousCount ? `동명이인 후보 ${ambiguousCount}명` : null,
    ].filter(Boolean).join(" / ") || "모든 참여자가 연결되었습니다.";

    for (const item of candidates) {
        const card = document.createElement("div");
        card.className = "session-participant-candidate";

        const head = document.createElement("div");
        head.className = "session-participant-candidate-head";

        const name = document.createElement("strong");
        name.className = "session-participant-candidate-name";
        name.textContent = item.name;

        const button = document.createElement("button");
        button.type = "button";
        button.className = "secondary-button secondary-button--compact";
        button.dataset.participantContactName = item.name;

        if (item.resolutionStatus === "ambiguous") {
            button.textContent = "새 contact 생성 불가";
            button.disabled = true;
        } else {
            button.textContent = "contact 추가";
        }

        head.append(name, button);

        const meta = document.createElement("p");
        meta.className = "session-participant-candidate-meta";
        meta.textContent = item.resolutionStatus === "ambiguous"
            ? `같은 이름의 contact가 ${item.matchedContactCount}명 있어 기존 대상을 선택해야 합니다.`
            : "현재 세션 맥락에서 연결된 contact가 없어 새 contact 후보로 표시했습니다.";

        card.append(head, meta);

        if (item.resolutionStatus === "ambiguous" && item.matchedContacts?.length) {
            const options = document.createElement("div");
            options.className = "session-participant-candidate-options";

            for (const match of item.matchedContacts) {
                const optionButton = document.createElement("button");
                optionButton.type = "button";
                optionButton.className = "secondary-button secondary-button--compact";
                optionButton.dataset.participantLinkName = item.name;
                optionButton.dataset.participantLinkContactId = match.contactId;
                optionButton.textContent = [
                    match.name || item.name,
                    match.jobTitle || null,
                    match.department || null,
                    match.email || null,
                ].filter(Boolean).join(" / ");
                options.append(optionButton);
            }

            card.append(options);
        }

        elements.sessionParticipantCandidatesList.append(card);
    }
}

export function renderParticipantFollowups() {
    if (
        !elements.sessionParticipantFollowupsPanel
        || !elements.sessionParticipantFollowupsList
        || !elements.sessionParticipantFollowupsStatus
    ) {
        return;
    }

    const followups = appState.session.participantFollowups ?? [];
    if (!appState.session.id || !followups.length) {
        elements.sessionParticipantFollowupsPanel.classList.add("hidden");
        elements.sessionParticipantFollowupsList.replaceChildren();
        elements.sessionParticipantFollowupsStatus.textContent = "아직 확인할 후속 작업이 없습니다.";
        return;
    }

    elements.sessionParticipantFollowupsPanel.classList.remove("hidden");
    elements.sessionParticipantFollowupsList.replaceChildren();

    const pendingCount = followups.filter((item) => item.followupStatus === "pending").length;
    const resolvedCount = followups.filter((item) => item.followupStatus === "resolved").length;
    elements.sessionParticipantFollowupsStatus.textContent = [
        pendingCount ? `처리 필요 ${pendingCount}건` : null,
        resolvedCount ? `해결 완료 ${resolvedCount}건` : null,
    ].filter(Boolean).join(" / ") || "후속 작업 상태를 불러왔습니다.";

    for (const item of followups) {
        const card = document.createElement("div");
        card.className = "history-card";

        const title = document.createElement("strong");
        title.className = "history-card-title";
        title.textContent = item.participantName;

        const meta = document.createElement("p");
        meta.className = "history-card-meta";
        meta.textContent = [
            item.followupStatus === "resolved" ? "해결됨" : "처리 필요",
            item.resolutionStatus,
            item.matchedContactCount ? `후보 ${item.matchedContactCount}명` : null,
        ].filter(Boolean).join(" / ");

        card.append(title, meta);
        elements.sessionParticipantFollowupsList.append(card);
    }
}

export async function refreshSessionParticipationState(sessionId = appState.session.id) {
    if (!sessionId) {
        setSessionParticipation(appState, {
            participants: [],
            participantCandidates: [],
            summary: null,
        });
        setSessionParticipantFollowups(appState, []);
        renderSessionSummary();
        renderParticipantCandidates();
        renderParticipantFollowups();
        return null;
    }

    try {
        const [participationPayload, followupPayload] = await Promise.all([
            fetchSessionParticipation(sessionId),
            fetchSessionParticipantFollowups(sessionId),
        ]);
        const payload = normalizeSessionParticipationPayload(participationPayload);
        const followups = normalizeParticipantFollowupListPayload(followupPayload);
        setSessionParticipation(appState, payload);
        setSessionParticipantFollowups(appState, followups);
        renderSessionSummary();
        renderParticipantCandidates();
        renderParticipantFollowups();
        return payload;
    } catch (error) {
        console.warn("[CAPS] 참여자 상세 조회 실패:", error);
    }

    renderSessionSummary();
    renderParticipantCandidates();
    renderParticipantFollowups();
    return null;
}

async function handleCreateParticipantContact(participantName) {
    if (!appState.session.id) {
        return;
    }

    const targetCandidate = appState.session.participantCandidates.find((item) => item.name === participantName);
    if (!targetCandidate) {
        flashStatus(elements.sessionStatus, "이미 처리된 참여자입니다.", "error");
        return;
    }

    if (targetCandidate.resolutionStatus !== "unmatched") {
        flashStatus(elements.sessionStatus, "동명이인 후보는 기존 contact를 직접 선택해야 합니다.", "error");
        return;
    }

    flashStatus(elements.sessionStatus, `${participantName} contact 생성 중...`, "idle");

    try {
        const payload = await createContactFromSessionParticipant(appState.session.id, {
            participantName,
            accountId: targetCandidate.accountId ?? appState.session.accountId ?? null,
        });
        await applyResolvedSessionPayload(payload, `${participantName} contact 연결 완료`);
    } catch (error) {
        console.error("[CAPS] 참여자 contact 생성 실패:", error);
        flashStatus(elements.sessionStatus, `${participantName} contact 연결 실패`, "error");
    }
}

async function handleLinkParticipantContact(participantName, contactId) {
    if (!appState.session.id) {
        return;
    }

    flashStatus(elements.sessionStatus, `${participantName} 기존 contact 연결 중...`, "idle");

    try {
        const payload = await linkContactForSessionParticipant(appState.session.id, {
            participantName,
            contactId,
        });
        await applyResolvedSessionPayload(payload, `${participantName} contact 연결 완료`);
    } catch (error) {
        console.error("[CAPS] 참여자 contact 연결 실패:", error);
        flashStatus(elements.sessionStatus, `${participantName} contact 연결 실패`, "error");
    }
}

async function applyResolvedSessionPayload(payload, successMessage) {
    const sessionPayload = normalizeSessionPayload(payload);
    setSession(appState, sessionPayload);
    await refreshSessionParticipationState(sessionPayload.id);
    void Promise.allSettled([
        refreshMeetingContextOptions(),
        refreshHistorySnapshot(),
    ]);
    flashStatus(elements.sessionStatus, successMessage, "live");
}
