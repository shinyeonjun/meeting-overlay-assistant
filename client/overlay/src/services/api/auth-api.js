/** 오버레이에서 공통 관련 auth api 서비스를 제공한다. */
import { requestJson, requestNoContent } from "./http-client.js";

export async function fetchAuthConfig() {
    return requestJson("/api/v1/auth/config", {
        includeAuth: false,
    });
}

export async function login({ loginId, password, clientType = "desktop" }) {
    return requestJson("/api/v1/auth/login", {
        method: "POST",
        includeAuth: false,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            login_id: loginId,
            password,
            client_type: clientType,
        }),
    });
}

export async function fetchCurrentUser() {
    return requestJson("/api/v1/auth/me");
}

export async function logout() {
    return requestNoContent("/api/v1/auth/logout", {
        method: "POST",
    });
}
