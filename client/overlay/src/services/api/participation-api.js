/** 오버레이에서 공통 관련 participation api 서비스를 제공한다. */
import { requestJson } from "./http-client.js";

export async function createContactFromSessionParticipant(
    sessionId,
    {
        participantName,
        accountId = null,
        email = null,
        jobTitle = null,
        department = null,
        notes = null,
    },
) {
    return requestJson(`/api/v1/sessions/${sessionId}/participants/contacts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            participant_name: participantName,
            account_id: accountId,
            email,
            job_title: jobTitle,
            department,
            notes,
        }),
    });
}

export async function linkContactForSessionParticipant(
    sessionId,
    {
        participantName,
        contactId,
    },
) {
    return requestJson(`/api/v1/sessions/${sessionId}/participants/links`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            participant_name: participantName,
            contact_id: contactId,
        }),
    });
}

export async function fetchSessionParticipation(sessionId) {
    return requestJson(`/api/v1/sessions/${sessionId}/participants`);
}

export async function fetchSessionParticipantFollowups(
    sessionId,
    {
        followupStatus = null,
    } = {},
) {
    const query = new URLSearchParams();
    if (followupStatus) {
        query.set("followup_status", followupStatus);
    }
    const suffix = query.size ? `?${query.toString()}` : "";
    return requestJson(`/api/v1/sessions/${sessionId}/participants/followups${suffix}`);
}
