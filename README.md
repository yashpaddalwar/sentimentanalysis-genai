# Call Sentiment Analyzer

An end-to-end GenAI application that analyzes call-center transcripts for
sentiment, emotion, and key operational KPIs using an LLM-powered LangGraph
pipeline.

## 🏗️ Architecture

```
┌─────────────────────┐        HTTPS (multipart/form-data)        ┌──────────────────────────┐
│   Next.js Frontend   │ ───────────────────────────────────────▶ │     FastAPI Backend        │
│   (Vercel)           │        X-API-Key header                   │     (Render)              │
│                       │ ◀─────────────────────────────────────── │                            │
│  - Login (localStorage)                    JSON response         │  POST /analyze             │
│  - Upload .txt transcript                                        │       │                    │
│  - Dashboard (Recharts)                                          │       ▼                    │
└─────────────────────┘                                            │  ┌─────────────────────┐  │
                                                                     │  │   LangGraph Pipeline │  │
                                                                     │  │                       │  │
                                                                     │  │ parse_transcript      │  │
                                                                     │  │       ▼               │  │
                                                                     │  │ sentence_sentiment ─▶ LLM (Groq: llama-3.3-70b-versatile)
                                                                     │  │       ▼               │  │
                                                                     │  │ aggregate_overall     │  │
                                                                     │  │       ▼               │  │
                                                                     │  │ kpi_extraction ────▶ LLM │
                                                                     │  │       ▼               │  │
                                                                     │  │ summary_node ──────▶ LLM │
                                                                     │  └─────────────────────┘  │
                                                                     └──────────────────────────┘
```

## 📁 Project Structure

```
/backend
  main.py                 # FastAPI app, /analyze endpoint, CORS, API key auth
  langgraph_pipeline.py   # LangGraph state + 5 nodes + compiled graph
  models.py               # Pydantic schemas (API + internal LLM outputs)
  requirements.txt
  Dockerfile
  .env.example

/frontend
  app/
    page.tsx              # Root redirect (login/dashboard)
    login/page.tsx
    dashboard/page.tsx
    layout.tsx
    globals.css
  components/
    UploadZone.tsx
    SummaryCard.tsx
    SentimentPieChart.tsx
    SentimentTrendChart.tsx
    EmotionBarChart.tsx
    KpiGrid.tsx
    SentenceTable.tsx
  lib/
    auth.ts
    api.ts
  types/index.ts
  package.json
  tailwind.config.ts
  postcss.config.js
  next.config.js
  tsconfig.json
  .env.local.example
```

## ⚙️ Environment Variables

### Backend (`/backend/.env`)

| Variable | Description | Example |
|---|---|---|
| `LLM_PROVIDER` | LLM provider selector | `groq` or `gemini` |
| `GROQ_API_KEY` | Groq API key | `gsk_...` |
| `GROQ_MODEL` | Groq model name | `llama-3.3-70b-versatile` |
| `GEMINI_API_KEY` | Gemini API key (if switching provider) | `AIza...` |
| `GEMINI_MODEL` | Gemini model name | `gemini-1.5-flash` |
| `FRONTEND_URL` | Comma-separated allowed CORS origins | `https://your-app.vercel.app` |
| `API_KEY` | Shared secret checked against `X-API-Key` header | `super-secret-key` |
| `PORT` | Port (Render sets this automatically) | `8000` |

### Frontend (`/frontend/.env.local`)

| Variable | Description | Example |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Backend base URL | `https://your-api.onrender.com` |
| `NEXT_PUBLIC_API_KEY` | Must match backend `API_KEY` | `super-secret-key` |
| `NEXT_PUBLIC_APP_USERNAME` | Hardcoded login username | `admin` |
| `NEXT_PUBLIC_APP_PASSWORD` | Hardcoded login password | `admin123` |

## 🚀 Local Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # fill in your keys
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
cp .env.local.example .env.local   # fill in your values
npm run dev
```

Visit `http://localhost:3000`.

## ☁️ Deployment

### Backend → Render
1. Push the `/backend` folder to a GitHub repo.
2. On Render: **New → Web Service** → connect repo → select **Docker** as the environment (Dockerfile is auto-detected).
3. Set environment variables in the Render dashboard (`GROQ_API_KEY`, `FRONTEND_URL`, `API_KEY`, `LLM_PROVIDER`, etc.).
4. Deploy. Render will build the Docker image and expose the service at `https://<service-name>.onrender.com`.
5. Confirm `GET /health` returns `{"status": "ok"}`.

### Frontend → Vercel
1. Push the `/frontend` folder to a GitHub repo (or same repo, different root directory).
2. On Vercel: **New Project** → import repo → set **Root Directory** to `frontend`.
3. Add environment variables (`NEXT_PUBLIC_API_URL` pointing to your Render URL, `NEXT_PUBLIC_API_KEY`, `NEXT_PUBLIC_APP_USERNAME`, `NEXT_PUBLIC_APP_PASSWORD`).
4. Deploy. Update the backend's `FRONTEND_URL` env var with the resulting Vercel domain and redeploy the backend.

## 🧠 Why LangGraph instead of n8n?

n8n is a great tool for wiring together pre-built integrations via a visual,
low-code canvas — but this project needed **fine-grained, code-first control
over a stateful, multi-step AI reasoning pipeline**, which is where LangGraph
has clear advantages for this use case:

- **Typed, shared state across steps** — LangGraph's `TypedDict` state object
  flows through every node (`parse_transcript → sentence_sentiment →
  aggregate_overall → kpi_extraction → summary_node`), so each node can read
  and enrich the same structured state, and the whole pipeline is fully
  type-checked in Python.
- **Native Python + LLM ecosystem integration** — since the pipeline lives in
  the same codebase as the FastAPI backend, it shares Pydantic models,
  structured-output parsing, and error handling with zero network hops or
  webhook glue — something n8n's HTTP-node-based orchestration can't offer as
  cleanly.
- **Deterministic graph execution with branching potential** — LangGraph
  models the pipeline as an explicit directed graph, which makes it trivial
  to later add conditional edges (e.g., skip KPI extraction on very short
  transcripts, or retry a node on LLM failure) — this is core to the
  "agentic orchestration" requirement of the assignment rather than a
  simple linear workflow.
- **Version-controlled, testable, and deployable as code** — the entire
  orchestration logic can be unit tested, code-reviewed, and deployed as a
  Docker container next to the API, whereas n8n workflows live outside the
  codebase and require a separately hosted n8n instance.

In short: LangGraph gives us **agentic, stateful, code-native orchestration**
that integrates directly with our Python/FastAPI stack, which is exactly what
this assignment's "agent orchestration" requirement calls for.