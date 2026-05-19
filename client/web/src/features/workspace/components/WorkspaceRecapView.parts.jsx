/** WorkspaceRecapView의 표시 전용 하위 컴포넌트. */

import { formatTimestamp } from "./WorkspaceRecapView.helpers.js";

export function ToolbarLink({ children, className = "", disabled = false, href, primary = false }) {
  const classes = [
    "caps-minutes-toolbar-button",
    primary ? "primary" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  if (!href || disabled) {
    return (
      <button className={classes} disabled type="button">
        {children}
      </button>
    );
  }

  return (
    <a className={classes} href={href} rel="noreferrer" target="_blank">
      {children}
    </a>
  );
}

export function EmptyLine({ children }) {
  return <p className="caps-minutes-empty">{children}</p>;
}

export function MinutesSection({ children, title }) {
  return (
    <section className="caps-minutes-section">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

export function MinutesList({ emptyText, items, ordered = false }) {
  if (!items.length) {
    return <EmptyLine>{emptyText}</EmptyLine>;
  }

  const Tag = ordered ? "ol" : "ul";
  return (
    <Tag className="caps-minutes-list">
      {items.map((item, index) => (
        <li key={`${item}-${index}`}>{item}</li>
      ))}
    </Tag>
  );
}

export function TopicBlock({ index, topic }) {
  return (
    <article className="caps-minutes-topic-block">
      <h3>
        {index + 1}. {topic.title}
      </h3>
      {topic.summary ? (
        <div className="caps-minutes-topic-body">
          <strong>정리된 내용</strong>
          <p>{topic.summary}</p>
        </div>
      ) : (
        <EmptyLine>정리된 논의 내용이 없습니다.</EmptyLine>
      )}
    </article>
  );
}

export function ActionList({ actions }) {
  if (!actions.length) {
    return <EmptyLine>정리된 후속 조치가 없습니다.</EmptyLine>;
  }

  return (
    <ol className="caps-minutes-action-list">
      {actions.map((item) => (
        <li key={item.id}>
          <span>{item.title}</span>
          <em>
            {[item.owner, item.dueDate].filter(Boolean).join(" · ") || "담당 미정"}
          </em>
        </li>
      ))}
    </ol>
  );
}

export function TranscriptExcerpt({ segments }) {
  if (!segments.length) {
    return <EmptyLine>교정된 대화록이 아직 없습니다.</EmptyLine>;
  }

  return (
    <div className="caps-minutes-transcript-list">
      {segments.map((segment, index) => (
        <div
          className="caps-minutes-transcript-row"
          key={segment.id || `${segment.start_ms}-${index}`}
        >
          <span>{formatTimestamp(segment.start_ms)}</span>
          <strong>{segment.speaker_label || "발화자"}</strong>
          <p>{segment.text || segment.content || ""}</p>
        </div>
      ))}
    </div>
  );
}

export function MinutesFallbackDocument({
  agenda,
  meta,
  recap,
  sessionTitle,
  sourceLabel,
  startedAtLabel,
  transcriptSegments,
}) {
  return (
    <article className="caps-minutes-page" aria-label="회의록 문서">
      <header className="caps-minutes-doc-header">
        <h1>회의록</h1>
      </header>

      <table className="caps-minutes-meta-table">
        <tbody>
          <tr>
            <th>회의 제목</th>
            <td colSpan="3">{sessionTitle}</td>
          </tr>
          <tr>
            <th>일시</th>
            <td>{startedAtLabel}</td>
            <th>소요 시간</th>
            <td>{meta.duration}</td>
          </tr>
          <tr>
            <th>참석자</th>
            <td colSpan="3">{meta.participants}</td>
          </tr>
          <tr>
            <th>소스</th>
            <td>{sourceLabel}</td>
            <th>발화자 수</th>
            <td>{meta.participantsCount}</td>
          </tr>
          <tr>
            <th>안건</th>
            <td colSpan="3">{agenda}</td>
          </tr>
        </tbody>
      </table>

      <MinutesSection title="1. 회의개요">
        <div className="caps-minutes-content-box compact">
          <MinutesList emptyText="회의 개요가 아직 없습니다." items={recap.overviewLines} />
        </div>
      </MinutesSection>

      <MinutesSection title="2. 회의내용">
        <div className="caps-minutes-content-box">
          {recap.topics.length > 0 ? (
            recap.topics.map((topic, index) => (
              <TopicBlock index={index} key={`${topic.title}-${index}`} topic={topic} />
            ))
          ) : (
            <EmptyLine>회의록 분석이 완료되면 회의내용이 표시됩니다.</EmptyLine>
          )}
        </div>
      </MinutesSection>

      <MinutesSection title="3. 결정사항">
        <div className="caps-minutes-content-box compact">
          <MinutesList
            emptyText="아직 확정된 결정사항이 없습니다."
            items={recap.decisions.slice(0, 8)}
            ordered
          />
        </div>
      </MinutesSection>

      <MinutesSection title="4. 후속 조치">
        <div className="caps-minutes-content-box compact">
          <ActionList actions={recap.actions} />
        </div>
      </MinutesSection>

      <MinutesSection title="5. 참고 대화록">
        <div className="caps-minutes-content-box transcript">
          <TranscriptExcerpt segments={transcriptSegments} />
        </div>
      </MinutesSection>
    </article>
  );
}
