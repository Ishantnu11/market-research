# Multi-Agent Market Research System

An advanced market research platform powered by **LangGraph**, **Gemini 2.5 Flash**, and **Tavily**. This system uses a multi-agent orchestrated workflow to perform deep web research, analyze competitors (SWOT), and generate executive-level Markdown reports with real-time SSE streaming.

**Stack**: LangGraph · Gemini 2.5 Flash · Groq (Fallback) · Tavily · FastAPI · React · Vite

## Project Structure

This project uses a unified directory structure for both the FastAPI backend and the React frontend:

- `main.py` — The core FastAPI application and LangGraph definition.
- `phase1_agent_core.py` — CLI-compatible version of the research agent logic.
- `App.jsx`, `main.jsx`, `index.html` — The React/Vite-powered frontend.
- `.env` — API keys and model configuration.
- `venv/` — Python virtual environment.

## Setup

### 1. Prerequisites
- Python 3.10+
- Node.js & npm

### 2. Installation
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Frontend dependencies
npm install
```

### 3. Configuration
Create/edit your `.env` file with the following keys:
```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
TAVILY_API_KEY=your_tavily_api_key
GROQ_API_KEY=your_groq_api_key (Optional fallback)
```

### 4. Running the Application
The application requires both the backend and frontend to be running simultaneously.

**Start the Backend:**
```bash
uvicorn main:app --port 8001
```

**Start the Frontend:**
```bash
npm run dev
# Opens at http://localhost:5173
```

## How It Works

### Agent Flow
1. **Researcher Node**: Executes parallel Tavily searches to gather raw market data and identify competitors.
2. **HITL Checkpoint**: The system pauses and streams identified competitors to the UI. The user can approve, edit, or request more searches.
3. **Analyst Node**: Performs cross-referencing, trend analysis, and SWOT generation.
4. **Writer Node**: Synthesizes analysis into a polished Markdown report with inline citations.
5. **Quality Check**: A self-correction loop that validates length, source count, and formatting.

## Key Optimizations
- **Parallel Research**: Concurrent web searching reduces researcher wait times by 50%.
- **Thread-Safe SSE**: Real-time event streaming via Server-Sent Events with optimized background thread communication.
- **Advanced LLM**: Configured for **Gemini 2.5 Flash** for superior reasoning speed and research depth.
- **Synchronized Ports**: Frontend and backend are pre-configured to communicate via port **8001**.
