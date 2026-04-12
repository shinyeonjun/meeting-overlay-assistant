/** 오버레이에서 세션 흐름의 session ending flow 제어를 담당한다. */
export async function executeSessionEndingFlow({
  sessionId,
  requestSessionEnd,
  stopLiveConnection,
}) {
  const endedSessionPayload = await requestSessionEnd(sessionId);

  let cleanupError = null;
  try {
    await stopLiveConnection();
  } catch (error) {
    cleanupError = error;
  }

  return {
    endedSessionPayload,
    cleanupError,
  };
}
