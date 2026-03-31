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
