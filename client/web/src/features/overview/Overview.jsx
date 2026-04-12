/** 웹 워크스페이스의 공통 기능 화면을 렌더링한다. */
import React, { useMemo } from "react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock3,
  FileText,
  Mic,
  NotebookPen,
  PlayCircle,
  Sparkles,
} from "lucide-react";

import {
  formatDateTime,
  formatSourceLabel,
  isRecoveryRequiredSession,
  resolveWorkflowStatus,
} from "../../app/workspace-model.js";
import "./overview.css";

function dedupeSessions(...groups) {
  const seen = new Set();
  return groups
    .flat()
    .filter(Boolean)
    .filter((session) => {
      if (seen.has(session.id)) {
        return false;
      }
      seen.add(session.id);
      return true;
    });
}

function buildHomeSummary({
  runningCount,
  recoveryCount,
  processingCount,
  carryCount,
}) {
  if (runningCount > 0) {
    return {
      title: "지금 이어서 볼 회의가 있습니다",
      description: `진행 중인 회의 ${runningCount}건을 바로 열 수 있습니다.`,
      tone: "live",
    };
  }

  if (recoveryCount > 0) {
    return {
      title: "복구가 필요한 회의가 있습니다",
      description: `비정상 종료된 세션 ${recoveryCount}건을 먼저 정리해두는 게 좋습니다.`,
      tone: "failed",
    };
  }

  if (processingCount > 0) {
    return {
      title: "정리 중인 노트가 있습니다",
      description: `후처리 또는 리포트 생성 중인 항목 ${processingCount}건을 확인해보세요.`,
      tone: "processing",
    };
  }

  if (carryCount > 0) {
    return {
      title: "이어질 메모가 남아 있습니다",
      description: `다음 회의로 이어질 메모 ${carryCount}건을 먼저 훑어보면 좋습니다.`,
      tone: "pending",
    };
  }

  return {
    title: "최근 회의를 다시 확인해보세요",
    description: "진행 중인 일은 없지만, 최근 노트를 검토하거나 다음 회의를 준비할 수 있습니다.",
    tone: "default",
  };
}

function HomeActionCard({ card }) {
  const Icon = card.icon;

  return (
    <button className={`home-action-card ${card.tone}`} onClick={card.onClick} type="button">
      <div className="home-action-card-head">
        <span className={`home-action-card-icon ${card.tone}`}>
          <Icon size={16} />
        </span>
        {card.badge ? <span className={`home-action-card-badge ${card.tone}`}>{card.badge}</span> : null}
      </div>

      <div className="home-action-card-copy">
        <strong>{card.title}</strong>
        <p>{card.description}</p>
        {card.meta ? <span>{card.meta}</span> : null}
      </div>

      <div className="home-action-card-foot">
        <span>{card.cta}</span>
        <ArrowRight size={15} />
      </div>
    </button>
  );
}

function HomeSupportList({ icon: Icon, title, items, emptyText, renderItem, ctaText, onCta }) {
  return (
    <section className="simple-home-card home-support-card">
      <div className="simple-home-card-header">
        <div className="simple-home-card-title">
          <Icon size={16} />
          <strong>{title}</strong>
        </div>
        {ctaText && onCta ? (
          <button className="home-support-link" onClick={onCta} type="button">
            {ctaText}
          </button>
        ) : null}
      </div>

      {items.length > 0 ? (
        <div className="simple-home-list">{items.map(renderItem)}</div>
      ) : (
        <div className="home-support-empty">
          <p>{emptyText}</p>
        </div>
      )}
    </section>
  );
}

function SessionSupportRow({ label, session, onOpenSession, reportStatuses }) {
  const workflow = resolveWorkflowStatus(session, reportStatuses?.[session.id]);

  return (
    <button className="simple-home-row compact" onClick={() => onOpenSession(session.id)} type="button">
      <div className="simple-home-row-copy">
        <strong>{session.title || "제목 없는 회의"}</strong>
        <span>
          {label} · {formatSourceLabel(session.primary_input_source)} · {formatDateTime(session.started_at)}
        </span>
      </div>
      <div className="simple-home-row-side">
        <span className={`simple-home-row-badge ${workflow.tone}`}>{workflow.label}</span>
        <ArrowRight size={14} />
      </div>
    </button>
  );
}

function CarryOverRow({ item, onOpenSession }) {
  return (
    <button className="simple-home-row compact" onClick={() => onOpenSession(item.session_id)} type="button">
      <div className="simple-home-row-copy">
        <strong>{item.title}</strong>
        <span>{item.session_title || "이어질 메모"}</span>
      </div>
      <ArrowRight size={14} />
    </button>
  );
}

export default function Overview({
  data,
  grouped,
  onOpenSession,
  onViewMeetings,
}) {
  const reportStatuses = data?.reportStatuses ?? {};
  const runningSessions = grouped.running ?? [];
  const failedSessions = grouped.failed ?? [];
  const processingSessions = grouped.processing ?? [];
  const completedSessions = dedupeSessions(grouped.ready ?? [], grouped.completed ?? []).slice(0, 3);

  const recoverySessions = useMemo(
    () => failedSessions.filter((session) => isRecoveryRequiredSession(session)),
    [failedSessions],
  );

  const carryItems = useMemo(
    () =>
      [
        ...(data?.carry_over?.action_items ?? []),
        ...(data?.carry_over?.decisions ?? []),
        ...(data?.carry_over?.questions ?? []),
      ].slice(0, 3),
    [data?.carry_over],
  );

  const summary = useMemo(
    () =>
      buildHomeSummary({
        runningCount: runningSessions.length,
        recoveryCount: recoverySessions.length,
        processingCount: processingSessions.length,
        carryCount: carryItems.length,
      }),
    [carryItems.length, processingSessions.length, recoverySessions.length, runningSessions.length],
  );

  const statusStats = useMemo(
    () => [
      {
        id: "running",
        label: "진행 중",
        value: runningSessions.length,
        tone: "live",
      },
      {
        id: "processing",
        label: "정리 중",
        value: processingSessions.length,
        tone: "processing",
      },
      {
        id: "recovery",
        label: "복구 필요",
        value: recoverySessions.length,
        tone: "failed",
      },
    ],
    [processingSessions.length, recoverySessions.length, runningSessions.length],
  );

  const actionCards = useMemo(() => {
    const cards = [];

    if (runningSessions[0]) {
      const session = runningSessions[0];
      cards.push({
        id: `running:${session.id}`,
        icon: PlayCircle,
        tone: "live",
        badge: "LIVE",
        title: "진행 중 회의 이어보기",
        description: session.title || "제목 없는 회의",
        meta: `${formatSourceLabel(session.primary_input_source)} · ${formatDateTime(session.started_at)}`,
        cta: "바로 열기",
        onClick: () => onOpenSession(session.id),
      });
    }

    if (recoverySessions[0]) {
      const session = recoverySessions[0];
      cards.push({
        id: `recovery:${session.id}`,
        icon: AlertTriangle,
        tone: "failed",
        badge: "복구 필요",
        title: "비정상 종료 세션 확인",
        description: session.title || "제목 없는 회의",
        meta: "삭제하거나 노트를 다시 만들 수 있습니다.",
        cta: "세션 열기",
        onClick: () => onOpenSession(session.id),
      });
    }

    if (processingSessions[0]) {
      const session = processingSessions[0];
      const workflow = resolveWorkflowStatus(session, reportStatuses?.[session.id]);
      cards.push({
        id: `processing:${session.id}`,
        icon: Clock3,
        tone: "processing",
        badge: workflow.label,
        title: "정리 중인 노트 확인",
        description: session.title || "제목 없는 회의",
        meta: "후처리 또는 리포트 생성 상태를 바로 볼 수 있습니다.",
        cta: "상태 보기",
        onClick: () => onOpenSession(session.id),
      });
    }

    if (completedSessions[0]) {
      const session = completedSessions[0];
      cards.push({
        id: `completed:${session.id}`,
        icon: CheckCircle2,
        tone: "completed",
        badge: "검토",
        title: "최신 노트 다시 보기",
        description: session.title || "제목 없는 회의",
        meta: `${formatSourceLabel(session.primary_input_source)} · ${formatDateTime(session.started_at)}`,
        cta: "노트 열기",
        onClick: () => onOpenSession(session.id),
      });
    }

    if (cards.length === 0) {
      cards.push({
        id: "meetings",
        icon: Mic,
        tone: "default",
        badge: null,
        title: "회의 화면 열기",
        description: "최근 회의를 확인하거나 새로 정리할 회의를 찾을 수 있습니다.",
        meta: "홈이 비어 있을 때는 회의 화면이 가장 빠른 시작점입니다.",
        cta: "회의로 이동",
        onClick: onViewMeetings,
      });
    }

    return cards.slice(0, 4);
  }, [
    completedSessions,
    onOpenSession,
    onViewMeetings,
    processingSessions,
    recoverySessions,
    reportStatuses,
    runningSessions,
  ]);

  return (
    <div className="simple-home-view animate-fade-in">
      <section className={`simple-home-hero home-hero-${summary.tone}`}>
        <div className="simple-home-copy">
          <span className="section-kicker">HOME</span>
          <h2>{summary.title}</h2>
          <p>{summary.description}</p>

          <div className="home-stat-grid">
            {statusStats.map((item) => (
              <div key={item.id} className={`home-stat-card ${item.tone}`}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </div>
            ))}
          </div>
        </div>

        <div className="simple-home-actions">
          <button className="session-action-button primary" onClick={onViewMeetings} type="button">
            <NotebookPen size={15} />
            회의 화면 열기
          </button>
        </div>
      </section>

      <section className="simple-home-card">
        <div className="simple-home-card-header">
          <div className="simple-home-card-title">
            <Sparkles size={16} />
            <strong>지금 바로 할 일</strong>
          </div>
          <span>{actionCards.length}건</span>
        </div>

        <div className="home-action-grid">
          {actionCards.map((card) => (
            <HomeActionCard key={card.id} card={card} />
          ))}
        </div>
      </section>

      <div className="simple-home-grid home-support-grid">
        <HomeSupportList
          ctaText={carryItems.length > 0 ? "회의로 이동" : null}
          emptyText="이어질 메모가 없으면 홈은 더 간결해집니다. 다음 회의를 열어 새 흐름을 시작해보세요."
          icon={NotebookPen}
          items={carryItems}
          onCta={onViewMeetings}
          renderItem={(item) => <CarryOverRow key={item.id || item.event_id} item={item} onOpenSession={onOpenSession} />}
          title="이어질 메모"
        />

        <HomeSupportList
          ctaText={completedSessions.length > 0 ? "최근 회의 보기" : null}
          emptyText="아직 다시 열어볼 최신 노트가 없습니다. 회의 화면에서 새 세션을 확인해보세요."
          icon={FileText}
          items={completedSessions}
          onCta={onViewMeetings}
          renderItem={(session) => (
            <SessionSupportRow
              key={session.id}
              label="최근 마감"
              onOpenSession={onOpenSession}
              reportStatuses={reportStatuses}
              session={session}
            />
          )}
          title="최근 마감된 노트"
        />
      </div>
    </div>
  );
}
