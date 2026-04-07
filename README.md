# Multi-Agent Market Research System

**Stack**: LangGraph · Groq (Llama 3.1) · Tavily · FastAPI · React · Vite

## Project Structure

```
market_research_agent/
├── backend/
│   ├── main.py          # Phase 1 (agents) + Phase 2 (FastAPI + SSE)
│   ├── requirements.txt
│   └── .env
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── index.css
    │   ├── main.jsx
    │   └── components/
    │       ├── QueryForm.jsx
    │       ├── AgentTimeline.jsx
    │       ├── HITLModal.jsx
    │       └── ReportViewer.jsx
    ├── index.html
    ├── package.json
    └── vite.config.js
```

## Setup

### 1. Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Add your API keys to .env
cp .env.example .env
# Edit .env and add GROQ_API_KEY and TAVILY_API_KEY

# Run the server
uvicorn main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

## How It Works

### Agent Flow

```
User Query
    │
    ▼
Researcher Node  ──► Tavily web search (2 queries)
    │                LLM extracts competitors
    ▼
HITL Checkpoint  ──► Frontend shows competitor list
    │                User: approve / search more / edit
    ▼
Analyst Node     ──► Cross-references sources
    │                Produces SWOT + competitor analysis
    ▼
Writer Node      ──► Drafts Markdown report
    │
    ▼
Quality Check    ──► Checks: Sources section? 2+ citations? 400+ words?
    │                If fail → loop back to Writer (max 3x)
    ▼
Final Report     ──► Streamed to frontend via SSE
```

### Key Architecture Decisions

**LangGraph state**: A `ResearchState` TypedDict flows through every node. 
Agents read and write to shared state — this is the "state management" talking point.

**SSE streaming**: The graph runs in a background thread. Each agent calls 
`push()` to put events into an `asyncio.Queue`. The FastAPI endpoint reads 
from the queue and streams SSE to the frontend in real time.

**HITL over SSE**: When the HITL node is reached, it sends a `hitl_required` 
event and blocks on the queue. The frontend shows a modal. When the user 
submits, the frontend POSTs to `/research/hitl-respond`, which puts a 
`hitl_response` back into the queue, unblocking the graph.

**Self-correction cycle**: `quality_check` is a conditional edge router. 
If the report fails validation (missing sources, too short), it returns 
`"writer"` instead of `"end"`, looping the graph. Rejection feedback is 
appended to the analysis so the Writer knows what to fix.

## Interview Talking Points

- **Agentic workflow**: "I built a multi-step reasoning system where each 
  agent has a single responsibility and passes structured state to the next."

- **State management**: "LangGraph maintains a persistent `ResearchState` 
  TypedDict across all nodes — no context is lost between agents."

- **Deterministic control**: "The graph architecture guarantees execution 
  order while letting the LLM be creative within each node."

- **Human-in-the-Loop**: "The system pauses mid-execution and streams a 
  checkpoint to the UI, waits for user input, then resumes — no polling needed."

- **Self-correction**: "The quality check is a conditional edge that creates 
  a cycle in the graph — the Writer can be sent back up to 3 times with 
  specific feedback before the report is accepted."

- **SSE over WebSockets**: "I used Server-Sent Events because the data flow 
  is one-directional from server to client — simpler than WebSockets and 
  works natively in browsers without a library."
