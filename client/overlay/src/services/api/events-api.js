/** 오버레이에서 공통 관련 events api 서비스를 제공한다. */
import { requestJson, requestNoContent } from "./http-client.js";

export async function fetchEventList(sessionId, params = {}) {
    const searchParams = new URLSearchParams();
    if (params.eventType) {
        searchParams.set("event_type", params.eventType);
    }
    if (params.state) {
        searchParams.set("state", params.state);
    }
    const query = searchParams.toString();
    return requestJson(`/api/v1/sessions/${sessionId}/events${query ? `?${query}` : ""}`);
}

export async function updateEvent(sessionId, eventId, payload) {
    return requestJson(`/api/v1/sessions/${sessionId}/events/${eventId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
}

export async function transitionEvent(sessionId, eventId, payload) {
    return requestJson(`/api/v1/sessions/${sessionId}/events/${eventId}/transition`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
}

export async function bulkTransitionEvents(sessionId, payload) {
    return requestJson(`/api/v1/sessions/${sessionId}/events/bulk-transition`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
}

export async function deleteEvent(sessionId, eventId) {
    return requestNoContent(`/api/v1/sessions/${sessionId}/events/${eventId}`, {
        method: "DELETE",
    });
}
