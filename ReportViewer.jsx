import { useEffect, useRef } from "react";

// Minimal Markdown → HTML renderer (no extra deps)
function mdToHtml(md) {
  return md
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/^# (.+)$/gm, "<h1>$1</h1>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/\[Source: (.+?)\]/g, '<a href="$1" target="_blank" class="source-link">[Source]</a>')
    .replace(/^- (.+)$/gm, "<li>$1</li>")
    .replace(/(<li>[\s\S]+?<\/li>)/g, "<ul>$1</ul>")
    .replace(/\n\n/g, "</p><p>")
    .replace(/^(?!<[hul])(.+)$/gm, "<p>$1</p>")
    .replace(/<p><\/p>/g, "");
}

export default function ReportViewer({ report }) {
  const ref = useRef(null);

  const download = () => {
    const blob = new Blob([report], { type: "text/markdown" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "market-research-report.md";
    a.click();
  };

  return (
    <div className="report-card">
      <div className="report-header">
        <span className="report-title">📄 Final Report</span>
        <button className="btn-outline" onClick={download}>
          ↓ Download .md
        </button>
      </div>
      <div
        className="report-body"
        dangerouslySetInnerHTML={{ __html: mdToHtml(report) }}
      />
    </div>
  );
}
