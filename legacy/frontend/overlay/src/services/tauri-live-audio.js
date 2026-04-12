import { listen } from "@tauri-apps/api/event";
import { invoke } from "@tauri-apps/api/core";

import { buildApiUrl } from "../config/runtime.js";

function hasWindowObject() {
    return typeof window !== "undefined";
}

export function isTauriRuntime() {
    if (!hasWindowObject()) {
        return false;
    }

    return Boolean(window.__TAURI_INTERNALS__ || window.__TAURI__);
}

export async function startTauriLiveAudioStream({
    pythonExe,
    scriptPath,
    sessionId,
    source,
    sampleRate,
    channels,
    chunkMs,
    deviceName = null,
}) {
    if (!isTauriRuntime()) {
        throw new Error("Tauri 런타임이 아닌 환경에서는 오디오 브리지를 시작할 수 없습니다.");
    }

    await invoke("start_live_audio_stream", {
        pythonExe,
        scriptPath,
        baseUrl: buildApiUrl(""),
        sessionId,
        source,
        sampleRate,
        channels,
        chunkMs,
        deviceName,
    });
}

export async function stopTauriLiveAudioStream() {
    if (!isTauriRuntime()) {
        return;
    }

    await invoke("stop_live_audio_stream");
}

export async function listenTauriEvent(eventName, handler) {
    if (!isTauriRuntime()) {
        return () => { };
    }

    return listen(eventName, handler);
}

export async function invokeTauri(command, payload = {}) {
    if (!isTauriRuntime()) {
        return null;
    }

    return invoke(command, payload);
}
