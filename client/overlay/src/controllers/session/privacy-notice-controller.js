import { elements } from "../../dom/elements.js";

export const PRIVACY_NOTICE_VERSION = "2026-05-v1";

const NOTICE_FALLBACK_MESSAGE = [
    "회의를 시작하면 음성이 녹음되고 전사됩니다.",
    "회의 종료 후 AI가 노트와 회의록 생성을 위해 내용을 분석합니다.",
    "참석자에게 고지했다면 확인을 눌러주세요.",
].join("\n\n");

export function requestPrivacyNoticeAcknowledgement() {
    if (
        !elements.privacyNoticeDialog ||
        !elements.privacyNoticeCheckbox ||
        !elements.privacyNoticeConfirmButton ||
        !elements.privacyNoticeCancelButton
    ) {
        return Promise.resolve(window.confirm(NOTICE_FALLBACK_MESSAGE));
    }

    const dialog = elements.privacyNoticeDialog;
    const checkbox = elements.privacyNoticeCheckbox;
    const confirmButton = elements.privacyNoticeConfirmButton;
    const cancelButton = elements.privacyNoticeCancelButton;

    checkbox.checked = false;
    confirmButton.disabled = true;
    dialog.classList.remove("hidden");
    dialog.setAttribute("aria-hidden", "false");
    checkbox.focus();

    return new Promise((resolve) => {
        const cleanup = () => {
            checkbox.removeEventListener("change", handleCheckboxChange);
            confirmButton.removeEventListener("click", handleConfirm);
            cancelButton.removeEventListener("click", handleCancel);
            window.removeEventListener("keydown", handleKeydown);
            dialog.classList.add("hidden");
            dialog.setAttribute("aria-hidden", "true");
        };

        const finish = (acknowledged) => {
            cleanup();
            resolve(acknowledged);
        };

        const handleCheckboxChange = () => {
            confirmButton.disabled = !checkbox.checked;
        };

        const handleConfirm = () => {
            finish(checkbox.checked);
        };

        const handleCancel = () => {
            finish(false);
        };

        const handleKeydown = (event) => {
            if (event.key === "Escape") {
                finish(false);
            }
        };

        checkbox.addEventListener("change", handleCheckboxChange);
        confirmButton.addEventListener("click", handleConfirm);
        cancelButton.addEventListener("click", handleCancel);
        window.addEventListener("keydown", handleKeydown);
    });
}
