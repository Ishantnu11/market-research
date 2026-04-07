import { useState } from "react";

const EXAMPLES = [
  "AI code assistant tools market 2024 — competitors, growth, trends",
  "Notion vs Linear vs Jira — project management SaaS market",
  "Electric vehicle charging infrastructure market analysis",
];

export default function QueryForm({ onSubmit, disabled }) {
  const [query, setQuery] = useState("");

  const handle = (e) => {
    e.preventDefault();
    if (query.trim()) onSubmit(query.trim());
  };

  return (
    <div className="query-card">
      <p className="query-label">Research query</p>
      <form onSubmit={handle} className="query-form">
        <textarea
          className="query-input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. AI code assistant tools market 2024 — competitors, growth, trends"
          rows={3}
          disabled={disabled}
        />
        <button className="btn-primary" type="submit" disabled={disabled || !query.trim()}>
          {disabled ? "Running…" : "Run Research"}
        </button>
      </form>
      <div className="examples">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            className="example-chip"
            onClick={() => setQuery(ex)}
            disabled={disabled}
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}
