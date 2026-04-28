/** 워크스페이스 회의 상세 화면의 레이아웃 컨테이너다. */
import React from "react";
import { AlertCircle, Loader } from "lucide-react";

import WorkspaceAudioPlayer from "./components/WorkspaceAudioPlayer.jsx";
import WorkspaceInsightPanel from "./components/WorkspaceInsightPanel.jsx";
import WorkspaceTranscriptPanel from "./components/WorkspaceTranscriptPanel.jsx";
import useWorkspaceAudioPlayback from "./hooks/useWorkspaceAudioPlayback.js";
import useWorkspaceSessionData from "./hooks/useWorkspaceSessionData.js";
import "./workspace-canvas.css";

export default function WorkspaceCanvas({
  onRefreshWorkspace,
  refreshToken,
  sessionId,
}) {
  const {
    actionError,
    actionNotice,
    canDownloadRecording,
    downloadHref,
    error,
    handleGenerateReport,
    handlePrimaryAction,
    hidePreviousNote,
    loading,
    overview,
    processingAction,
    reportArtifactUrls,
    reportDetail,
    reportStatus,
    reportWorkflow,
    session,
    showTranscriptProgressHero,
    transcript,
    transcriptLoading,
    visibleLatestReport,
    workflow,
  } = useWorkspaceSessionData({
    onRefreshWorkspace,
    refreshToken,
    sessionId,
  });

  const {
    activeClip,
    audioCurrentTime,
    audioDuration,
    audioReady,
    audioRef,
    handlePlayTranscriptClip,
    handleSeekAudio,
    handleToggleAudioPlayback,
    loadingAudio,
    playingAudio,
  } = useWorkspaceAudioPlayback({
    canDownloadRecording,
    sessionId,
  });

  if (loading) {
    return (
      <div className="workspace-state-view">
        <Loader className="spinner" size={28} />
        <p>회의 화면을 불러오는 중입니다.</p>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="workspace-state-view error">
        <AlertCircle size={28} />
        <h3>회의 화면을 열 수 없습니다.</h3>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div
      className={`caps-meeting-workspace animate-fade-in ${canDownloadRecording ? "has-audio-player" : ""}`}
    >
      <WorkspaceTranscriptPanel
        actionError={actionError}
        actionNotice={actionNotice}
        activeClipId={activeClip?.id ?? null}
        canDownloadRecording={canDownloadRecording}
        downloadHref={downloadHref}
        onGenerateReport={handleGenerateReport}
        onPlayTranscriptClip={handlePlayTranscriptClip}
        onPrimaryAction={handlePrimaryAction}
        overview={overview}
        processingAction={processingAction}
        reportArtifactUrls={reportArtifactUrls}
        reportDetail={reportDetail}
        reportStatus={reportStatus}
        reportWorkflow={reportWorkflow}
        session={session}
        showTranscriptProgressHero={showTranscriptProgressHero}
        transcript={transcript}
        transcriptLoading={transcriptLoading}
        visibleLatestReport={visibleLatestReport}
        workflow={workflow}
      />

      <WorkspaceInsightPanel
        actionNotice={actionNotice}
        hidePreviousNote={hidePreviousNote}
        latestReport={visibleLatestReport}
        overview={overview}
        reportStatus={reportStatus}
        session={session}
      />

      {canDownloadRecording ? (
        <WorkspaceAudioPlayer
          audioCurrentTime={audioCurrentTime}
          audioDuration={audioDuration}
          audioReady={audioReady}
          audioRef={audioRef}
          loadingAudio={loadingAudio}
          onSeekAudio={handleSeekAudio}
          onToggleAudioPlayback={handleToggleAudioPlayback}
          playingAudio={playingAudio}
        />
      ) : null}
    </div>
  );
}
