/** 오버레이에서 공통 관련 runtime api 서비스를 제공한다. */
import { requestLiveJson } from "./http-client.js";

export async function fetchRuntimeReadiness() {
    return requestLiveJson("/api/v1/runtime/readiness");
}

export async function fetchRuntimeMonitor() {
    return requestLiveJson("/api/v1/runtime/monitor");
}
