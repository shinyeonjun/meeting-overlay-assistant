/** 오버레이에서 공통 흐름의 ui web workspace controller 제어를 담당한다. */
import { getApiBaseUrl } from "../../config/runtime.js";
import { buildWebWorkspaceUrl } from "../../config/web-workspace.js";
import { appState } from "../../state/app-state.js";

export function openWebWorkspace(sectionId = "overview") {
    const workspaceUrl = buildWebWorkspaceUrl({
        sectionId,
        sessionId: appState.session.id,
        serverBaseUrl: getApiBaseUrl(),
    });

    window.open(workspaceUrl, "_blank", "noopener,noreferrer");
    return workspaceUrl;
}
