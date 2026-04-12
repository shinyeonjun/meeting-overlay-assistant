/** 오버레이에서 공통 관련 tauri live audio 서비스를 제공한다. */
import { listen } from "@tauri-apps/api/event";
import { invoke } from "@tauri-apps/api/core";

import { buildLiveApiUrl } from "../config/runtime.js";
import { getPersistedAccessToken } from "./auth-storage.js";

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
    preprocess = {},
    accessToken = null,
}) {
    if (!isTauriRuntime()) {
        throw new Error("Tauri 런타임이 아닌 환경에서는 오디오 브리지를 시작할 수 없습니다.");
    }

    await invoke("start_live_audio_stream", {
        pythonExe,
        scriptPath,
        baseUrl: buildLiveApiUrl(""),
        sessionId,
        source,
        sampleRate,
        channels,
        chunkMs,
        deviceName,
        accessToken: accessToken ?? getPersistedAccessToken(),
        silenceGateEnabled: preprocess.silenceGateEnabled === true,
        silenceGateMinRms: Number(preprocess.silenceGateMinRms ?? 0),
        silenceGateHoldChunks: Number(preprocess.silenceGateHoldChunks ?? 0),
    });
}

export async function prewarmTauriLiveAudioStream({
    pythonExe,
    scriptPath,
    source,
    sampleRate,
    channels,
    chunkMs,
    deviceName = null,
    preprocess = {},
}) {
    if (!isTauriRuntime()) {
        return;
    }

    await invoke("prewarm_live_audio_stream", {
        pythonExe,
        scriptPath,
        source,
        sampleRate,
        channels,
        chunkMs,
        deviceName,
        silenceGateEnabled: preprocess.silenceGateEnabled === true,
        silenceGateMinRms: Number(preprocess.silenceGateMinRms ?? 0),
        silenceGateHoldChunks: Number(preprocess.silenceGateHoldChunks ?? 0),
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
