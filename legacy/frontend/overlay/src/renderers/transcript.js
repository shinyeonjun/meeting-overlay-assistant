export function renderTranscriptCurrent({ speakerElement, textElement }, item) {
    speakerElement.textContent = item?.speaker_label ?? "";
    textElement.textContent = item?.text ?? "아직 들어온 발화가 없습니다.";
}

export function renderTranscriptHistory() {
    return undefined;
}
