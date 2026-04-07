import { useEffect, useRef } from "react";

const AGENT_COLORS = {
  Researcher: "#3b82f6",
  Analyst: "#f59e0b",
  Writer: "#10b981",
};

const icons = {
  agent_start: "▶",
  agent_done: "✓",
  hitl_approved: "👤",
  quality_check: "⚙",
};

export default function AgentTimeline({ events, running }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  return (
    <div className="timeline-card">
      <div className="timeline-header">
        <span>Agent Activity</span>
        {running && <span className="pulse-dot" />}
      </div>
      <div className="timeline-list">
        {events.map((ev, i) => {
          const agent = ev.data?.agent;
          const color = AGENT_COLORS[agent] || "#94a3b8";
          const isQC = ev.type === "quality_check";
          const qcOk = ev.data?.status === "accepted";

          return (
            <div key={i} className="timeline-item">
              <div
                className="timeline-dot"
                style={{ background: isQC ? (qcOk ? "#10b981" : "#ef4444") : color }}
              >
                {icons[ev.type] || "•"}
              </div>
              <div className="timeline-content">
                {agent && (
                  <span className="agent-tag" style={{ color }}>
                    {agent}
                  </span>
                )}
                {isQC && (
                  <span className="agent-tag" style={{ color: qcOk ? "#10b981" : "#ef4444" }}>
                    Quality Check
                  </span>
                )}
                <span className="timeline-msg">
                  {ev.data?.message ||
                    (isQC
                      ? qcOk
                        ? `✓ Accepted — ${ev.data?.reason}`
                        : `✗ Rejected — ${ev.data?.issues?.join(", ")}`
                      : ev.type === "hitl_approved"
                      ? `Competitors confirmed: ${ev.data?.competitors?.join(", ")}`
                      : "")}
                </span>
                {ev.type === "agent_done" && ev.data?.competitors && (
                  <div className="competitor-chips">
                    {ev.data.competitors.map((c) => (
                      <span key={c} className="chip">{c}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
        {running && (
          <div className="timeline-item">
            <div className="timeline-dot pulsing">…</div>
            <span className="timeline-msg muted">Agent working…</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
