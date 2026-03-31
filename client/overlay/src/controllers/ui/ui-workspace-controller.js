import { elements } from "../../dom/elements.js";

export function openWorkspace() {
    elements.workspace?.classList.remove("collapsed");
    elements.workspace?.setAttribute("aria-hidden", "false");
    elements.togglePanel?.classList.add("active");
    document.body.classList.add("workspace-open");
}

export function closeWorkspace() {
    elements.workspace?.classList.add("collapsed");
    elements.workspace?.setAttribute("aria-hidden", "true");
    elements.togglePanel?.classList.remove("active");
    document.body.classList.remove("workspace-open");
}

export function activateTab(tabName) {
    for (const tab of elements.tabs) {
        tab.classList.toggle("active", tab.dataset.tab === tabName);
    }

    for (const body of elements.tabBodies) {
        body.classList.toggle("active", body.id === `tab-${tabName}`);
    }
}

export function toggleCaptionBody() {
    const isCollapsed = elements.captionBox?.classList.toggle("collapsed");
    if (elements.captionToggle) {
        elements.captionToggle.textContent = isCollapsed ? "+" : "-";
    }
}
