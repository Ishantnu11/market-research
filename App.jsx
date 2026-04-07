import { useState, useRef } from "react";
import QueryForm from "./QueryForm";
import AgentTimeline from "./AgentTimeline";
import HITLModal from "./HITLModal";
import ReportViewer from "./ReportViewer";
import "./index.css";

export default function App() {
  const [phase, setPhase] = useState("idle"); // idle | running | hitl | done | error
  const [events, setEvents] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [hitlData, setHitlData] = useState(null);
  const [report, setReport] = useState("");
  const [error, setError] = useState("");
  const esRef = useRef(null);
  
  // Use relative path if backend is serving the frontend, 
  // or use environment variable for cross-domain deployment.
  const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

  const addEvent = (type, data) =>
    setEvents((prev) => [...prev, { type, data, ts: Date.now() }]);

  const startResearch = async (query) => {
    setPhase("running");
    setEvents([]);
    setReport("");
    setError("");

    const res = await fetch(`${API_BASE}/research/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    const parseSSE = (chunk) => {
      buffer += chunk;
      const parts = buffer.split("\n\n");
      buffer = parts.pop();
      for (const part of parts) {
        const lines = part.split("\n");
        let event = "message", dataStr = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) event = line.slice(7);
          if (line.startsWith("data: ")) dataStr = line.slice(6);
        }
        if (!dataStr) continue;
        try {
          const data = JSON.parse(dataStr);
          handleEvent(event, data);
        } catch {}
      }
    };

    const handleEvent = (event, data) => {
      if (event === "session_start") {
        setSessionId(data.session_id);
      } else if (event === "agent_start" || event === "agent_done") {
        addEvent(event, data);
      } else if (event === "hitl_required") {
        setHitlData(data);
        setPhase("hitl");
      } else if (event === "hitl_approved") {
        setHitlData(null);
        setPhase("running");
        addEvent("hitl_approved", data);
      } else if (event === "quality_check") {
        addEvent("quality_check", data);
      } else if (event === "complete") {
        setReport(data.report);
        setPhase("done");
      } else if (event === "error") {
        setError(data.message);
        setPhase("error");
      }
    };

    (async () => {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        parseSSE(decoder.decode(value, { stream: true }));
      }
    })();
  };

  const submitHITL = async (choice, competitors) => {
    await fetch(`${API_BASE}/research/hitl-respond`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, choice, competitors }),
    });
    setPhase("running");
  };

  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <span className="logo">⬡</span>
          <h1>Market Research Agent</h1>
          <span className="badge">Multi-Agent · LangGraph</span>
        </div>
      </header>

      <main className="main">
        <QueryForm onSubmit={startResearch} disabled={phase === "running" || phase === "hitl"} />

        {phase !== "idle" && (
          <div className="workspace">
            <AgentTimeline events={events} running={phase === "running"} />

            {phase === "hitl" && hitlData && (
              <HITLModal data={hitlData} onSubmit={submitHITL} />
            )}

            {phase === "done" && report && (
              <ReportViewer report={report} />
            )}

            {phase === "error" && (
              <div className="error-box">
                <strong>Error:</strong> {error}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
