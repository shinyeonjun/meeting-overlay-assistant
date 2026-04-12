import { requestJson } from "./http-client.js";

export async function fetchRuntimeReadiness() {
    return requestJson("/api/v1/runtime/readiness");
}

export async function fetchRuntimeMonitor() {
    return requestJson("/api/v1/runtime/monitor");
}
