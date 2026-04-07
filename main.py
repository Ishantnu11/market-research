"""
Multi-Agent Market Research System
Phase 1 (Agents) + Phase 2 (FastAPI + SSE)
"""

import os
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import TypedDict, Literal, AsyncIterator
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import openai

from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, END

load_dotenv()

app = FastAPI(title="Market Research Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────
# PHASE 1 — SHARED STATE
# ─────────────────────────────────────────

class ResearchState(TypedDict):
    query: str
    raw_research: list[dict]
    competitors: list[str]
    hitl_approved: bool
    hitl_pending: bool          # True = waiting for frontend approval
    hitl_choice: str            # "approve" | "search_more" | set by frontend
    analysis: str
    report: str
    revision_count: int
    messages: list[str]
    stream_queue: object        # asyncio.Queue — used to push SSE events


# ─────────────────────────────────────────
# PHASE 1 — LLM & TOOLS
# ─────────────────────────────────────────

class OpenAIClient:
    def __init__(self, model, api_key=None, temperature=0.3, api_base=None, api_type=None, api_version=None):
        if api_key:
            openai.api_key = api_key
        if api_base:
            openai.api_base = api_base
        elif os.getenv("OPENAI_API_BASE"):
            openai.api_base = os.getenv("OPENAI_API_BASE")
        if api_type:
            openai.api_type = api_type
        elif os.getenv("OPENAI_API_TYPE"):
            openai.api_type = os.getenv("OPENAI_API_TYPE")
        if api_version:
            openai.api_version = api_version
        elif os.getenv("OPENAI_API_VERSION"):
            openai.api_version = os.getenv("OPENAI_API_VERSION")
        self.model = model
        self.temperature = temperature

    def invoke(self, prompt):
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=2000,
        )
        class Result:
            def __init__(self, content):
                self.content = content
        return Result(response.choices[0].message["content"].strip())


def create_llm():
    if os.getenv("GEMINI_API_KEY"):
        return OpenAIClient(
            model=os.getenv("GEMINI_MODEL", "gemini-1.3"),
            api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0.3,
            api_base=os.getenv("GEMINI_API_BASE"),
            api_type=os.getenv("GEMINI_API_TYPE"),
            api_version=os.getenv("GEMINI_API_VERSION"),
        )

    if os.getenv("OPENAI_API_KEY"):
        return OpenAIClient(
            model=os.getenv("OPENAI_MODEL", "openai/gpt-oss-120b"),
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.3,
        )

    if os.getenv("GROQ_API_KEY"):
        preferred = os.getenv("GROQ_MODEL")
        fallback_models = [
            preferred,
            "llama-3-4b-instant",
            "llama-3-7b-instant",
            "llama-3-8b-instant",
        ]
        last_error = None
        for model in [m for m in fallback_models if m]:
            try:
                return ChatGroq(
                    model=model,
                    api_key=os.getenv("GROQ_API_KEY"),
                    temperature=0.3,
                )
            except Exception as e:
                last_error = e
        raise RuntimeError(
            f"Unable to initialize ChatGroq. Tried models: {[m for m in fallback_models if m]}. "
            f"Last error: {last_error}"
        )

    raise RuntimeError("No GEMINI_API_KEY, OPENAI_API_KEY, or GROQ_API_KEY configured for the LLM.")

llm = create_llm()

tavily = TavilySearch(
    max_results=5,
    api_key=os.getenv("TAVILY_API_KEY"),
)

executor = ThreadPoolExecutor(max_workers=4)

def normalize_tavily_results(results):
    if isinstance(results, dict):
        for key in ("results", "data", "items", "hits"):
            if key in results and isinstance(results[key], list):
                return results[key]
        return [results]
    return results or []


def safe_invoke(fn, *args, timeout=45, **kwargs):
    future = executor.submit(fn, *args, **kwargs)
    try:
        return future.result(timeout=timeout)
    except FutureTimeoutError:
        future.cancel()
        raise TimeoutError(f"{fn.__name__} timed out after {timeout} seconds")


def push(state: ResearchState, event: str, data: dict):
    """Push an SSE event into the stream queue."""
    q: asyncio.Queue = state["stream_queue"]
    try:
        q.put_nowait({"event": event, "data": data})
    except Exception:
        pass


# ─────────────────────────────────────────
# PHASE 1 — AGENT NODES
# ─────────────────────────────────────────

def researcher_node(state: ResearchState) -> ResearchState:
    push(state, "agent_start", {"agent": "Researcher", "message": "Searching the web..."})

    results = normalize_tavily_results(safe_invoke(tavily.invoke, state["query"], timeout=30))
    competitor_results = normalize_tavily_results(
        safe_invoke(tavily.invoke, f"{state['query']} top competitors market share 2024", timeout=30)
    )

    seen, unique = set(), []
    for r in results + competitor_results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)

    state["raw_research"] = unique

    research_text = "\n\n".join([
        f"Source: {r['url']}\n{r['content']}" for r in unique[:6]
    ])

    response = safe_invoke(llm.invoke, f"""
Extract the top 5 competitors or key players from this market research.
Return ONLY a JSON array of names. Example: ["Company A", "Company B"]

Context: {state['query']}
Data: {research_text[:3000]}
""", timeout=60)

    try:
        c = response.content
        state["competitors"] = json.loads(c[c.find("["):c.rfind("]")+1])
    except Exception:
        state["competitors"] = ["Could not extract — check raw research"]

    push(state, "agent_done", {
        "agent": "Researcher",
        "message": f"Found {len(unique)} sources",
        "competitors": state["competitors"],
    })
    return state


def hitl_node(state: ResearchState) -> ResearchState:
    """Pauses execution and waits for frontend approval via the queue."""
    push(state, "hitl_required", {
        "message": "Please review the competitor list",
        "competitors": state["competitors"],
    })

    # Block until frontend sends approval back through the queue
    q: asyncio.Queue = state["stream_queue"]
    # We use a sentinel value put back by the /hitl-respond endpoint
    while True:
        try:
            item = q.get_nowait()
            if item.get("event") == "hitl_response":
                choice = item["data"].get("choice", "approve")
                if choice == "search_more":
                    push(state, "agent_start", {"agent": "Researcher", "message": "Searching for more competitors..."})
                    extra = normalize_tavily_results(
                        safe_invoke(tavily.invoke, f"{state['query']} industry players market leaders analysis", timeout=30)
                    )
                    state["raw_research"] += extra
                    resp = llm.invoke(
                        f"Extract 8 competitors as JSON array from:\n{' '.join([r['content'] for r in extra[:3]])[:2000]}"
                    )
                    try:
                        c = resp.content
                        state["competitors"] = json.loads(c[c.find("["):c.rfind("]")+1])
                    except Exception:
                        pass
                elif choice == "manual":
                    state["competitors"] = item["data"].get("competitors", state["competitors"])

                state["hitl_approved"] = True
                push(state, "hitl_approved", {"competitors": state["competitors"]})
                return state
        except Exception:
            import time
            time.sleep(0.3)


def analyst_node(state: ResearchState) -> ResearchState:
    push(state, "agent_start", {"agent": "Analyst", "message": "Running SWOT and competitor analysis..."})

    research_text = "\n\n".join([
        f"Source: {r['url']}\nContent: {r['content']}"
        for r in state["raw_research"][:8]
    ])

    response = safe_invoke(llm.invoke, f"""
You are a senior market analyst. Produce a structured analysis.

Query: {state['query']}
Key Competitors: {', '.join(state['competitors'])}

Research:
{research_text[:4000]}

Write sections:
1. **Market Overview** — size, growth rate, key trends
2. **Competitor Analysis** — each player's positioning
3. **SWOT Analysis** — for the overall market
4. **Key Insights** — 3-5 actionable points with [Source: URL] citations

Cite sources using [Source: URL] format throughout.
""", timeout=60)

    state["analysis"] = response.content
    push(state, "agent_done", {"agent": "Analyst", "message": "Analysis complete"})
    return state


def writer_node(state: ResearchState) -> ResearchState:
    attempt = state["revision_count"] + 1
    push(state, "agent_start", {
        "agent": "Writer",
        "message": f"Drafting report (attempt {attempt})..."
    })

    response = safe_invoke(llm.invoke, f"""
You are a professional market research writer. Write an executive-level report in Markdown.

Query: {state['query']}

Analysis:
{state['analysis']}

Requirements:
- ## Executive Summary at the top
- ## Sources section at the bottom with all cited URLs
- Every statistic needs an inline [Source: URL] citation
- ## Methodology section at the end
- Minimum 600 words
- CRITICAL: ## Sources section is MANDATORY
""", timeout=60)

    state["report"] = response.content
    state["revision_count"] += 1
    push(state, "agent_done", {
        "agent": "Writer",
        "message": f"Draft {state['revision_count']} complete"
    })
    return state


# ─────────────────────────────────────────
# PHASE 1 — SELF-CORRECTION ROUTER
# ─────────────────────────────────────────

def quality_check(state: ResearchState) -> Literal["writer", "end"]:
    report = state["report"]

    if state["revision_count"] >= 3:
        push(state, "quality_check", {"status": "accepted", "reason": "Max revisions reached"})
        return "end"

    issues = []
    if "## Sources" not in report:
        issues.append("missing ## Sources section")
    if report.count("[Source:") < 2:
        issues.append(f"only {report.count('[Source:')} citations (need 2+)")
    if len(report.split()) < 400:
        issues.append("report too short")

    if issues:
        push(state, "quality_check", {"status": "rejected", "issues": issues})
        state["analysis"] += f"\n\n⚠️ REVISION REQUIRED: {', '.join(issues)}. Fix these."
        return "writer"

    push(state, "quality_check", {"status": "accepted", "reason": "All checks passed"})
    return "end"


# ─────────────────────────────────────────
# PHASE 1 — BUILD GRAPH
# ─────────────────────────────────────────

def build_graph():
    g = StateGraph(ResearchState)
    g.add_node("researcher", researcher_node)
    g.add_node("hitl", hitl_node)
    g.add_node("analyst", analyst_node)
    g.add_node("writer", writer_node)
    g.set_entry_point("researcher")
    g.add_edge("researcher", "hitl")
    g.add_edge("hitl", "analyst")
    g.add_edge("analyst", "writer")
    g.add_conditional_edges("writer", quality_check, {"writer": "writer", "end": END})
    return g.compile()


graph = build_graph()


# ─────────────────────────────────────────
# PHASE 2 — API MODELS
# ─────────────────────────────────────────

class ResearchRequest(BaseModel):
    query: str

class HITLResponse(BaseModel):
    session_id: str
    choice: Literal["approve", "search_more", "manual"]
    competitors: list[str] = []


# In-memory session store (use Redis in production)
sessions: dict[str, asyncio.Queue] = {}


# ─────────────────────────────────────────
# PHASE 2 — SSE STREAM ENDPOINT
# ─────────────────────────────────────────

@app.post("/research/stream")
async def research_stream(req: ResearchRequest):
    """
    Starts a research session and streams SSE events.
    The graph runs in a background thread (since LangGraph nodes are sync).
    """
    import uuid, threading

    session_id = str(uuid.uuid4())
    q: asyncio.Queue = asyncio.Queue()
    sessions[session_id] = q

    # Send session_id as first event so frontend can store it for HITL
    await q.put({"event": "session_start", "data": {"session_id": session_id}})

    initial_state: ResearchState = {
        "query": req.query,
        "raw_research": [],
        "competitors": [],
        "hitl_approved": False,
        "hitl_pending": False,
        "hitl_choice": "",
        "analysis": "",
        "report": "",
        "revision_count": 0,
        "messages": [],
        "stream_queue": q,
    }

    def run_graph():
        try:
            result = graph.invoke(initial_state)
            q.put_nowait({
                "event": "complete",
                "data": {"report": result["report"], "messages": result["messages"]}
            })
        except Exception as e:
            q.put_nowait({"event": "error", "data": {"message": str(e)}})
        finally:
            q.put_nowait({"event": "done", "data": {}})

    thread = threading.Thread(target=run_graph, daemon=True)
    thread.start()

    async def event_generator() -> AsyncIterator[str]:
        while True:
            try:
                item = await asyncio.wait_for(q.get(), timeout=180.0)
                yield f"event: {item['event']}\ndata: {json.dumps(item['data'])}\n\n"
                if item["event"] in ("done", "error"):
                    break
            except asyncio.TimeoutError:
                yield "event: ping\ndata: {}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/research/hitl-respond")
async def hitl_respond(resp: HITLResponse):
    """Frontend calls this to send the HITL approval back to the running graph."""
    q = sessions.get(resp.session_id)
    if not q:
        raise HTTPException(status_code=404, detail="Session not found")

    await q.put({
        "event": "hitl_response",
        "data": {"choice": resp.choice, "competitors": resp.competitors}
    })
    return {"status": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok"}
