"""
Multi-Agent Market Research System — Phase 1: Agent Core
Stack: LangGraph + Groq (Llama 3.1) + Tavily
"""

import os
import json
from typing import TypedDict, Annotated, Literal
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.graph import StateGraph, END

load_dotenv()

# ─────────────────────────────────────────
# 1. SHARED STATE
# ─────────────────────────────────────────

class ResearchState(TypedDict):
    query: str                        # original user query
    raw_research: list[dict]          # Researcher output: [{title, url, content}]
    competitors: list[str]            # extracted competitor names
    hitl_approved: bool               # did the user approve the competitor list?
    analysis: str                     # Analyst output: SWOT + trends text
    report: str                       # Writer output: final Markdown report
    revision_count: int               # how many times Writer has been sent back
    messages: list[str]               # event log shown to frontend


# ─────────────────────────────────────────
# 2. TOOLS & LLM
# ─────────────────────────────────────────

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.3,
)

tavily = TavilySearchResults(
    max_results=5,
    api_key=os.getenv("TAVILY_API_KEY"),
)


# ─────────────────────────────────────────
# 3. AGENT NODES
# ─────────────────────────────────────────

def researcher_node(state: ResearchState) -> ResearchState:
    """Scours the web for raw market data."""
    print("\n[RESEARCHER] Starting web search...")
    state["messages"].append("🔍 Researcher: Searching the web...")

    results = tavily.invoke(state["query"])

    # Also search for competitors specifically
    competitor_results = tavily.invoke(f"{state['query']} top competitors market share")

    all_results = results + competitor_results

    # Deduplicate by URL
    seen = set()
    unique_results = []
    for r in all_results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique_results.append(r)

    state["raw_research"] = unique_results

    # Extract competitor names using LLM
    research_text = "\n\n".join([
        f"Source: {r['url']}\n{r['content']}" for r in unique_results[:6]
    ])

    competitor_prompt = f"""
You are a market research analyst. Based on the following research data, extract a list of 
the top 5 competitors or key players in the market. Return ONLY a JSON array of company/product names.
Example: ["Company A", "Company B", "Company C"]

Research data:
{research_text[:3000]}

Query context: {state['query']}
"""
    response = llm.invoke(competitor_prompt)
    
    try:
        # Extract JSON array from response
        content = response.content
        start = content.find("[")
        end = content.rfind("]") + 1
        competitors = json.loads(content[start:end])
    except Exception:
        competitors = ["Unable to extract competitors — check raw research"]

    state["competitors"] = competitors
    state["messages"].append(
        f"✅ Researcher: Found {len(unique_results)} sources, identified {len(competitors)} competitors."
    )
    print(f"[RESEARCHER] Done. Sources: {len(unique_results)}, Competitors: {competitors}")
    return state


def hitl_node(state: ResearchState) -> ResearchState:
    """Human-in-the-Loop: pauses and asks the user to approve the competitor list."""
    print("\n[HITL] Awaiting human approval...")
    
    print("\n" + "="*50)
    print("📋 HUMAN-IN-THE-LOOP CHECKPOINT")
    print("="*50)
    print(f"\nThe Researcher has identified these competitors:\n")
    for i, c in enumerate(state["competitors"], 1):
        print(f"  {i}. {c}")
    
    print("\nOptions:")
    print("  [1] Proceed with this list")
    print("  [2] Search for more competitors")
    print("  [3] Manually enter competitor names")
    
    choice = input("\nYour choice (1/2/3): ").strip()

    if choice == "2":
        print("\n[HITL] Re-running Researcher with broader search...")
        state["messages"].append("👤 Human: Requested broader competitor search.")
        broader_results = tavily.invoke(
            f"{state['query']} industry players analysis report 2024"
        )
        state["raw_research"] += broader_results
        # Re-extract competitors
        research_text = "\n\n".join([r["content"] for r in broader_results[:4]])
        response = llm.invoke(
            f"Extract top 8 competitors from this text as a JSON array:\n{research_text[:2000]}"
        )
        try:
            content = response.content
            start = content.find("[")
            end = content.rfind("]") + 1
            state["competitors"] = json.loads(content[start:end])
        except Exception:
            pass

    elif choice == "3":
        manual = input("Enter competitor names (comma-separated): ")
        state["competitors"] = [c.strip() for c in manual.split(",")]
        state["messages"].append("👤 Human: Manually entered competitor list.")

    else:
        state["messages"].append("👤 Human: Approved competitor list.")

    state["hitl_approved"] = True
    print(f"[HITL] Approved. Proceeding with: {state['competitors']}")
    return state


def analyst_node(state: ResearchState) -> ResearchState:
    """Cross-references data, runs SWOT and competitor analysis."""
    print("\n[ANALYST] Starting analysis...")
    state["messages"].append("📊 Analyst: Running SWOT and competitor analysis...")

    research_text = "\n\n".join([
        f"Source: {r['url']}\nContent: {r['content']}"
        for r in state["raw_research"][:8]
    ])

    analysis_prompt = f"""
You are a senior market analyst. Analyze the following research data and produce a structured analysis.

Query: {state['query']}
Key Competitors Identified: {', '.join(state['competitors'])}

Research Data:
{research_text[:4000]}

Produce a thorough analysis with these sections:
1. **Market Overview** — size, growth rate, key trends
2. **Competitor Analysis** — strengths and positioning of each key player
3. **SWOT Analysis** — for the overall market
4. **Key Insights** — 3-5 actionable data points with source citations (cite as [Source: URL])

Be specific. Include numbers, percentages, and dates where available from the sources.
Always cite sources using [Source: URL] format.
"""

    response = llm.invoke(analysis_prompt)
    state["analysis"] = response.content
    state["messages"].append("✅ Analyst: Analysis complete.")
    print("[ANALYST] Done.")
    return state


def writer_node(state: ResearchState) -> ResearchState:
    """Synthesizes everything into a professional Markdown report."""
    print("\n[WRITER] Drafting report...")
    state["messages"].append(
        f"✍️ Writer: Drafting report (attempt {state['revision_count'] + 1})..."
    )

    writer_prompt = f"""
You are a professional market research writer. Using the analysis below, write a polished,
executive-level market research report in Markdown format.

Original Query: {state['query']}

Analysis:
{state['analysis']}

Requirements:
- Use proper Markdown headings (##, ###)
- Include an Executive Summary at the top
- Include a Sources section at the bottom listing all cited URLs
- Every claim with a number or statistic MUST have a [Source: URL] citation inline
- End with a "Methodology" section explaining how the research was conducted
- Minimum 600 words

CRITICAL: The report MUST include a populated ## Sources section at the end.
If any section lacks citations, add them from the research data.
"""

    response = llm.invoke(writer_prompt)
    state["report"] = response.content
    state["revision_count"] += 1
    state["messages"].append(f"✍️ Writer: Draft {state['revision_count']} complete.")
    print(f"[WRITER] Draft {state['revision_count']} done.")
    return state


# ─────────────────────────────────────────
# 4. SELF-CORRECTION ROUTER
# ─────────────────────────────────────────

def quality_check(state: ResearchState) -> Literal["writer", "end"]:
    """
    Analyst reviews Writer's output.
    Rejects if: no Sources section, fewer than 2 citations, or too short.
    Max 2 revision cycles to avoid infinite loops.
    """
    report = state["report"]
    revision_count = state["revision_count"]

    if revision_count >= 3:
        print("[QUALITY CHECK] Max revisions reached. Accepting report.")
        state["messages"].append("✅ Quality check: Report accepted (max revisions reached).")
        return "end"

    issues = []

    if "## Sources" not in report and "## Source" not in report:
        issues.append("missing Sources section")

    citation_count = report.count("[Source:")
    if citation_count < 2:
        issues.append(f"only {citation_count} citations found (need at least 2)")

    if len(report.split()) < 400:
        issues.append("report is too short (under 400 words)")

    if issues:
        print(f"[QUALITY CHECK] Rejected. Issues: {issues}. Sending back to Writer.")
        state["messages"].append(
            f"🔄 Quality check: Rejected — {', '.join(issues)}. Revising..."
        )
        # Augment analysis with rejection feedback so Writer knows what to fix
        state["analysis"] += f"\n\n⚠️ REVISION REQUIRED: Previous draft was rejected for: {', '.join(issues)}. Fix these issues."
        return "writer"

    print("[QUALITY CHECK] Report accepted.")
    state["messages"].append("✅ Quality check: Report accepted.")
    return "end"


# ─────────────────────────────────────────
# 5. BUILD THE GRAPH
# ─────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(ResearchState)

    graph.add_node("researcher", researcher_node)
    graph.add_node("hitl", hitl_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("writer", writer_node)

    graph.set_entry_point("researcher")
    graph.add_edge("researcher", "hitl")
    graph.add_edge("hitl", "analyst")
    graph.add_edge("analyst", "writer")

    # Self-correction cycle: Writer → quality_check → Writer or END
    graph.add_conditional_edges(
        "writer",
        quality_check,
        {
            "writer": "writer",   # loop back
            "end": END,
        }
    )

    return graph.compile()


# ─────────────────────────────────────────
# 6. RUN
# ─────────────────────────────────────────

if __name__ == "__main__":
    app = build_graph()

    query = input("Enter your market research query: ").strip()
    if not query:
        query = "AI code assistant tools market analysis 2024 — competitors, growth, trends"

    initial_state: ResearchState = {
        "query": query,
        "raw_research": [],
        "competitors": [],
        "hitl_approved": False,
        "analysis": "",
        "report": "",
        "revision_count": 0,
        "messages": [],
    }

    print(f"\n🚀 Starting research for: '{query}'\n")
    final_state = app.invoke(initial_state)

    print("\n" + "="*60)
    print("📄 FINAL REPORT")
    print("="*60)
    print(final_state["report"])

    # Save report to file
    with open("research_report.md", "w") as f:
        f.write(final_state["report"])
    print("\n✅ Report saved to research_report.md")

    print("\n📋 Event Log:")
    for msg in final_state["messages"]:
        print(f"  {msg}")
