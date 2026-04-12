import { requestLiveJson } from "./http-client.js";

export async function fetchRuntimeReadiness() {
    return requestLiveJson("/api/v1/runtime/readiness");
}

export async function fetchRuntimeMonitor() {
    return requestLiveJson("/api/v1/runtime/monitor");
}
