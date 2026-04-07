import { useState } from "react";

export default function HITLModal({ data, onSubmit }) {
  const [custom, setCustom] = useState(data.competitors.join(", "));
  const [mode, setMode] = useState("approve"); // approve | search_more | manual

  const handleSubmit = () => {
    if (mode === "manual") {
      const list = custom.split(",").map((s) => s.trim()).filter(Boolean);
      onSubmit("manual", list);
    } else {
      onSubmit(mode, []);
    }
  };

  return (
    <div className="hitl-overlay">
      <div className="hitl-card">
        <div className="hitl-badge">⏸ Human-in-the-Loop</div>
        <h2 className="hitl-title">Review Competitor List</h2>
        <p className="hitl-desc">
          The Researcher identified these competitors. How would you like to proceed?
        </p>

        <div className="competitor-grid">
          {data.competitors.map((c, i) => (
            <div key={i} className="competitor-item">
              <span className="competitor-num">{i + 1}</span>
              {c}
            </div>
          ))}
        </div>

        <div className="hitl-options">
          {[
            { id: "approve", label: "✓ Proceed with this list" },
            { id: "search_more", label: "⟳ Search for more competitors" },
            { id: "manual", label: "✎ Edit manually" },
          ].map((opt) => (
            <button
              key={opt.id}
              className={`hitl-option ${mode === opt.id ? "active" : ""}`}
              onClick={() => setMode(opt.id)}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {mode === "manual" && (
          <textarea
            className="query-input"
            value={custom}
            onChange={(e) => setCustom(e.target.value)}
            rows={2}
            placeholder="Company A, Company B, Company C"
          />
        )}

        <button className="btn-primary" onClick={handleSubmit}>
          Continue Research →
        </button>
      </div>
    </div>
  );
}
