# Call Sentiment Analyzer

An end-to-end GenAI application that analyzes customer-support call transcripts for **sentiment, emotion, conversation trends, call-center KPIs, and an overall summary**.

The application combines a **Next.js frontend**, **FastAPI backend**, and **LangGraph-based GenAI orchestration pipeline**. The system is designed to work with realistic, imperfect transcripts rather than assuming that every line is already a clean sentence.

---

## 🧠 What the Application Does

The application accepts a `.txt` call transcript and produces:

* Overall call sentiment
* Overall confidence
* Sentence/utterance-level sentiment
* Detected emotions
* Reasoning for each sentiment classification
* Customer satisfaction estimate (CSAT)
* Escalation risk
* Resolution status
* Agent sentiment
* Customer sentiment
* Sentiment trend
* Agent politeness score
* Key topics
* Concise call summary

The analysis is returned as a strict, validated JSON response and visualized through an interactive dashboard.

---

## 🏗️ Architecture

![Architecture Diagram](./call-sentiment.png)
---

## 🔄 Analysis Flow

The pipeline intentionally uses **exactly three LLM calls per transcript upload**.

### Step 1 — Smart Transcript Parsing

The backend first preprocesses the uploaded transcript without using an LLM.

The parser handles imperfect real-world transcript formats such as:

```text
Agent: Hello sir, welcome to support.

Customer: Yes actually I have a problem with my payment.

Agent:
Let me check that transaction for you.

Customer:
Haan please check karo, amount already deduct hua hai.
```

It supports:

* Speaker labels such as `Agent:` and `Customer:`
* Alternative speaker formats such as `Agent -`
* Bracketed speakers such as `[Agent]:`
* Timestamp prefixes
* Multiline speaker turns
* Continuation lines
* Mixed-language / code-switched conversations
* Transcripts where punctuation and formatting are inconsistent

The system deliberately analyzes **conversational turns / analysis units** instead of blindly assuming every punctuation boundary represents a meaningful conversational event.

This reduces unnecessary structured-output tokens and makes the downstream analysis more reliable.

---

### Step 2 — Sentence / Utterance Sentiment Analysis

**LLM Call #1**

Each conversational analysis unit is classified for:

* Sentiment
* Emotion
* Confidence
* Short reasoning

The LLM is explicitly instructed to keep **sentiment and emotion separate**.

For example:

```text
Sentiment: Neutral
Emotion: Frustration
```

is valid.

Similarly:

```text
Sentiment: Neutral
Emotion: Surprise
```

is valid.

This prevents emotions such as `Surprise`, `Frustration`, `Polite`, or `Curiosity` from being incorrectly treated as sentiment categories.

The model output is validated through a Pydantic structured-output schema and normalized before being returned to the frontend.

---

### Step 3 — Overall Sentiment Aggregation

**No LLM call**

Overall sentiment is calculated deterministically in Python from the sentence/utterance-level results.

The sentiment scores are mapped as:

```text
Positive = +1
Neutral  =  0
Negative = -1
```

The calculation also takes the model confidence into account.

This is intentionally implemented as deterministic Python logic instead of asking another LLM to "guess" the overall sentiment.

This gives the application:

* Lower latency
* Lower token usage
* More deterministic behavior
* Reproducible results
* Better separation between AI reasoning and business logic

---

### Step 4 — KPI Extraction

**LLM Call #2**

The KPI node receives the transcript and sentence-level analysis and extracts:

```text
CSAT score estimate
Escalation risk
Resolution status
Agent sentiment average
Customer sentiment average
Sentiment trend
Politeness score
Key topics
```

The output is again validated against a Pydantic schema.

The LLM is instructed to be evidence-based and avoid inventing information.

---

### Step 5 — Call Summary

**LLM Call #3**

The final LLM call generates a concise 2–3 sentence summary covering:

1. The customer's issue
2. What the agent did
3. The outcome

The summary model is explicitly instructed to avoid hallucinating details that are not supported by the transcript.

---

## ⚡ Why There Are Exactly 3 LLM Calls

The system deliberately keeps the LLM budget fixed at:

```text
1 transcript upload
        ↓
LLM #1 → Sentence / utterance sentiment
        ↓
Python → Overall sentiment aggregation
        ↓
LLM #2 → KPI extraction
        ↓
LLM #3 → Call summary
```

There is no separate LLM call for:

* Parsing
* Overall sentiment
* Frontend chart generation
* Sentiment aggregation
* Data formatting

This keeps the pipeline efficient while still demonstrating multiple meaningful GenAI stages.

The KPI and summary stages are independent after overall aggregation, so they can be represented as separate branches in LangGraph.

---

## 🤖 Why LangGraph?

LangGraph is used as the orchestration layer because the application needs a **stateful, code-first graph for multiple AI-processing stages**.

The shared graph state allows nodes to pass information through the pipeline:

```text
Transcript
   ↓
Parsed Turns
   ↓
Sentence-Level Sentiment
   ↓
Overall Sentiment
   ↓
KPIs + Summary
```

Each node has one focused responsibility.

This gives the system:

* Explicit graph-based orchestration
* Shared typed state
* Clear separation of responsibilities
* Structured LLM outputs
* Deterministic non-LLM processing
* Easy extension with conditional branches
* Python-native integration with FastAPI and Pydantic
* Better testability and version control

LangGraph is therefore being used as an actual orchestration layer rather than simply calling an LLM sequentially from an API endpoint.

---

## 🆚 Why LangGraph Instead of n8n?

n8n is excellent for low-code automation and connecting external services.

For this application, however, the core problem is an **AI reasoning pipeline implemented directly in Python**.

LangGraph is a better fit because:

### Typed Shared State

A shared `TypedDict` state flows across the graph, allowing every node to read previous results and add new results.

### Code-First AI Orchestration

The pipeline lives directly alongside the FastAPI backend and can reuse:

* Python logic
* Pydantic schemas
* LLM integrations
* validation
* exception handling
* application configuration

### Explicit Graph Execution

The AI workflow is represented as an actual graph rather than a collection of unrelated API calls.

This makes future conditional execution straightforward.

For example:

```text
Short transcript
      ↓
Skip expensive analysis
```

or:

```text
High escalation risk
      ↓
Run additional specialist analysis
```

can be introduced without redesigning the entire backend.

### Testability

The individual nodes can be unit-tested independently.

For example:

```text
parse_transcript()
aggregate_overall()
normalize_sentiment()
```

do not require an LLM call to test.

### Version Control

The orchestration logic is plain Python and therefore can be:

* code-reviewed
* version-controlled
* tested
* containerized
* deployed through CI/CD

This makes LangGraph a strong fit for a production-oriented GenAI application.

---

# 🔐 Authentication and Security

The application uses two separate security layers.

## Frontend Authentication

The frontend contains a simple interview-assignment login mechanism.

Credentials are stored as server-side environment variables:

```env
APP_USERNAME=admin
APP_PASSWORD=admin123
```

The frontend creates a signed session token using:

```env
AUTH_SECRET=<long-random-secret>
```

The session is validated before dashboard/API access.

`NEXT_PUBLIC_` is intentionally avoided for credentials because variables with the `NEXT_PUBLIC_` prefix are bundled into client-side JavaScript.

---

## Backend Authentication

The backend additionally supports a shared API key:

```http
X-API-Key: <secret>
```

The API key is kept server-side:

```env
API_KEY=<backend-secret>
```

The frontend does not need to expose the backend API key directly to the browser.

The Next.js API route acts as an authenticated proxy between the browser and the FastAPI backend.

---

# 📊 Dashboard

The dashboard provides:

### Overall Summary

Displays:

* Overall sentiment
* Overall confidence
* AI-generated call summary

### Sentiment Distribution

A Recharts visualization showing:

```text
Positive
Negative
Neutral
```

### Sentiment Trend

Shows how sentiment changes throughout the conversation.

### Emotion Distribution

Displays the emotions detected across the conversation.

### KPI Dashboard

Displays:

* CSAT estimate
* Escalation risk
* Resolution status
* Sentiment trend
* Politeness score
* Agent sentiment
* Customer sentiment
* Key topics

### Detailed Conversation Analysis

The sentence/utterance analysis table includes:

* Speaker
* Conversation text
* Sentiment
* Emotion
* Confidence
* Reasoning

It also supports:

* Search
* Sentiment filtering
* Expandable reasoning
* JSON export

---

# 🧩 Structured LLM Output

The application uses Pydantic models with LangChain structured output.

Conceptually:

```text
LLM
 ↓
Structured Output
 ↓
Pydantic Validation
 ↓
Python Object
 ↓
API Response
```

This is preferable to relying on arbitrary free-form JSON generated by the model.

The internal LLM schema is intentionally tolerant enough to handle model variation, while deterministic Python normalization converts the result into the application's strict API contract.

---

# 📝 API Contract

## `POST /analyze`

Accepts:

```text
multipart/form-data
```

with:

```text
file=<transcript.txt>
```

Returns:

```json
{
  "overall_sentiment": "Positive",
  "overall_confidence": 0.84,
  "summary": "The customer initially reported...",
  "sentences": [
    {
      "text": "I have a problem with my payment.",
      "speaker": "Customer",
      "sentiment": "Negative",
      "emotion": "frustration",
      "confidence": 0.91,
      "reasoning": "The customer reports a payment issue."
    }
  ],
  "kpis": {
    "csat_score_estimate": 8.5,
    "escalation_risk": "Low",
    "resolution_status": "Resolved",
    "agent_sentiment_avg": "Calm and professional",
    "customer_sentiment_avg": "Initially frustrated, later relieved",
    "sentiment_trend": "Improving",
    "politeness_score": 9.0,
    "key_topics": [
      "payment issue",
      "refund",
      "transaction reversal"
    ]
  }
}
```

---

# 🩺 Health Check

The backend exposes:

```http
GET /health
```

Expected response:

```json
{
  "status": "ok",
  "service": "call-sentiment-analyzer"
}
```

This endpoint can be used for deployment verification and service monitoring.

---

# ⚙️ Environment Variables

## Backend

Create:

```text
backend/.env
```

Example:

```env
LLM_PROVIDER=groq

GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b

FRONTEND_URL=http://localhost:3000

API_KEY=your_backend_api_key

MAX_UPLOAD_BYTES=2097152
MAX_ANALYSIS_UNITS=80
```

### Provider Switching

The provider is configurable through:

```env
LLM_PROVIDER=groq
```

The LLM factory can be extended to another provider without changing the LangGraph node design.

For example, Gemini can be configured with:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=your_gemini_model
```

The application therefore keeps the orchestration layer provider-agnostic.

> Set `GROQ_MODEL` to the exact GPT-OSS model identifier available in your Groq account. The value above is an example for a GPT-OSS deployment.

---

## Frontend

For the browser-facing application, use:

```env
APP_USERNAME=admin
APP_PASSWORD=admin123

AUTH_SECRET=replace-with-a-long-random-secret

BACKEND_URL=https://your-backend.onrender.com

BACKEND_API_KEY=your_backend_api_key
```

For local development:

```env
APP_USERNAME=admin
APP_PASSWORD=admin123

AUTH_SECRET=replace-with-a-long-random-secret

BACKEND_URL=http://localhost:8000

BACKEND_API_KEY=your_backend_api_key
```

Do **not** expose backend secrets through `NEXT_PUBLIC_*` variables.

---

# 🛠️ Local Development with uv

The backend uses **uv** for Python project and dependency management.

## Install uv

Verify installation:

```bash
uv --version
```

Official uv documentation:

https://docs.astral.sh/uv/

---

## Create a New Backend Project

When creating the project from scratch:

```bash
cd backend
uv init
```

`uv init` creates a Python project configuration based on `pyproject.toml`.

If the project already contains a `pyproject.toml`, do not run `uv init` again.

---

## Create the Virtual Environment

```bash
uv venv
```

This creates:

```text
.venv
```

in the project directory.

### Windows

```powershell
.venv\Scripts\activate
```

### macOS / Linux

```bash
source .venv/bin/activate
```

Activation is optional when using `uv run`, because uv can automatically use the project environment.

---

## Add Backend Dependencies

For a new project, dependencies can be added using `uv add`.

For example:

```bash
uv add fastapi
uv add "uvicorn[standard]"
uv add python-multipart
uv add pydantic
uv add python-dotenv
uv add langchain
uv add langchain-core
uv add langchain-groq
uv add langchain-google-genai
uv add langgraph
```

For an existing repository containing the project's `pyproject.toml` and lockfile, the preferred command is:

```bash
uv sync
```

`uv add` updates the project's dependency metadata, while `uv sync` synchronizes the environment with the project's declared dependencies.

---

## Run the Backend

With the environment activated:

```bash
uv run uvicorn main:app --reload --port 8000
```

Alternatively, with the virtual environment already activated:

```bash
uvicorn main:app --reload --port 8000
```

Using `uv run` ensures the command executes using the project's managed environment.

The backend will be available at:

```text
http://localhost:8000
```

Swagger documentation:

```text
http://localhost:8000/docs
```

Health check:

```text
http://localhost:8000/health
```

---

# 🌐 Frontend Local Setup

From the frontend directory:

```bash
npm install
```

Create the environment file:

```text
.env.local
```

Add the required values:

```env
APP_USERNAME=admin
APP_PASSWORD=admin123
AUTH_SECRET=your-long-random-secret
BACKEND_URL=http://localhost:8000
BACKEND_API_KEY=your_backend_api_key
```

Start Next.js:

```bash
npm run dev
```

Open:

```text
http://localhost:3000
```

---

# 🚀 Deployment

## Backend — Render

Deploy the FastAPI application as a Render Web Service.

Configure the production environment variables:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=your_gpt_oss_model_id

FRONTEND_URL=https://your-frontend.vercel.app

API_KEY=your_backend_api_key

MAX_UPLOAD_BYTES=2097152
MAX_ANALYSIS_UNITS=80
```

Render provides the production service URL:

```text
https://your-service.onrender.com
```

Verify:

```text
https://your-service.onrender.com/health
```

---

## Frontend — Vercel

Deploy the Next.js application to Vercel.

Configure:

```env
APP_USERNAME=admin
APP_PASSWORD=admin123

AUTH_SECRET=your-long-random-secret

BACKEND_URL=https://your-service.onrender.com

BACKEND_API_KEY=your_backend_api_key
```

After deployment, update the Render environment variable:

```env
FRONTEND_URL=https://your-frontend.vercel.app
```

The frontend then communicates with the FastAPI backend through the authenticated Next.js API route.

---

# 🔒 Security Notes

This application is designed as an interview assignment and therefore uses intentionally lightweight authentication.

It is **not intended to replace a production identity provider** such as OAuth/OIDC, Auth0, Clerk, Cognito, or enterprise SSO.

Important security practices implemented here include:

* Server-side credential configuration
* Signed session tokens
* Private authentication secret
* Backend API-key validation
* No browser exposure of the backend API key
* Configurable CORS
* Upload-size validation
* UTF-8 validation
* Structured response validation
* Sanitized backend traces
* Avoiding persistence of complete transcript contents in debug traces

---

# 🧯 Error Handling

The backend explicitly handles:

* Missing transcript
* Empty files
* Invalid file extensions
* Invalid UTF-8 content
* Oversized files
* Unparseable transcripts
* Excessive analysis units
* LLM failures
* Invalid structured output
* Incomplete sentence-level responses
* Invalid API response construction

The system intentionally does not silently attach an incomplete LLM result to the wrong transcript unit.

That is important for analytical correctness.

---

# 🎯 Design Decisions

## Why parse transcripts locally?

Transcript parsing is deterministic preprocessing.

There is no reason to spend an LLM call on a task that can be handled reliably with Python.

This reduces:

* Cost
* Latency
* Token usage
* Failure points

---

## Why calculate overall sentiment in Python?

The overall sentiment is derived from already-classified utterances.

A deterministic weighted aggregation is more reproducible than asking another LLM to summarize sentiment numerically.

---

## Why use structured output?

A call-center analytics API should not depend on the model returning perfectly formatted arbitrary JSON.

Structured output plus Pydantic validation gives the application a predictable contract.

---

## Why separate KPI extraction and summarization?

They represent different analytical responsibilities.

### KPI extraction

Produces structured operational metrics.

### Summary

Produces human-readable narrative output.

Keeping these as separate LangGraph nodes makes the workflow easier to understand, test and extend.

---

## Why not add more LLM calls?

Additional LLM calls would increase latency and failure probability without providing meaningful value for the current requirements.

The current architecture intentionally keeps the core AI pipeline at:

```text
LLM #1 → Fine-grained sentiment
LLM #2 → Operational KPIs
LLM #3 → Summary
```

Everything else is deterministic application logic.

---

# 📈 Future Extensions

The current architecture can be extended without redesigning the application.

Potential future additions include:

* Conditional escalation analysis
* Agent coaching recommendations
* Call-quality scoring
* PII detection and redaction
* Multi-language transcript support
* Streaming analysis
* Persistent analysis history
* Authentication through enterprise SSO
* Human feedback on model results
* Evaluation datasets and automated quality benchmarks
* LangGraph checkpointing
* Observability and tracing
* Additional LLM providers

These features can be added as additional LangGraph nodes or conditional branches when required.

---

# ✅ Key Takeaway

The application is intentionally designed as a **code-first GenAI pipeline**, not simply a chatbot around an LLM.

The complete processing flow is:

```text
TXT Transcript
      ↓
Smart Python Transcript Parser
      ↓
LLM #1 — Sentiment + Emotion + Reasoning
      ↓
Python — Deterministic Overall Sentiment
      ↓
┌─────────────────────┬─────────────────────┐
│                     │                     │
LLM #2                LLM #3
KPI Extraction        Call Summary
│                     │
└──────────────┬──────┘
               ↓
        Pydantic Validation
               ↓
        FastAPI JSON Response
               ↓
      Next.js Analytics Dashboard
```

This design keeps the system:

**AI-powered + structured + deterministic where possible + provider-configurable + deployable + extensible.**
