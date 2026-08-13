import os
import re
import time
import json
from typing import TypedDict, List, Dict, Optional, Any

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

from models import SentenceListLLMOutput, KPILLMOutput
from logger_config import get_logger

logger = get_logger("langgraph_pipeline")


# =========================================================
# LLM Provider Factory (swappable via LLM_PROVIDER env var)
# =========================================================

def get_llm(temperature: float = 0.0):
    provider = os.getenv("LLM_PROVIDER", "groq").lower()

    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            temperature=temperature,
            api_key=os.getenv("GROQ_API_KEY"),
        )

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
            temperature=temperature,
            google_api_key=os.getenv("GEMINI_API_KEY"),
        )

    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")


# =========================================================
# Shared LangGraph State
# =========================================================

class GraphState(TypedDict):
    request_id: str
    raw_text: str
    turns: List[Dict[str, Optional[str]]]
    sentence_results: List[Dict[str, Any]]
    overall_sentiment: str
    overall_confidence: float
    kpis: Dict[str, Any]
    summary: str
    error: Optional[str]


# =========================================================
# Helpers
# =========================================================

SPEAKER_LINE_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 _\-]{0,30}?)\s*:\s*(.+)$")


def split_sentences(text: str) -> List[str]:
    text = text.strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


# =========================================================
# Node 1: parse_transcript
# =========================================================

def parse_transcript_node(state: GraphState) -> Dict[str, Any]:
    rid = state.get("request_id", "unknown")
    start = time.perf_counter()
    logger.info(f"[{rid}] NODE START -> parse_transcript")

    raw_text = state["raw_text"]
    lines = [l for l in raw_text.splitlines() if l.strip()]

    turns: List[Dict[str, Optional[str]]] = []
    for line in lines:
        match = SPEAKER_LINE_RE.match(line)
        if match:
            speaker, text = match.group(1).strip(), match.group(2).strip()
            for sentence in split_sentences(text):
                turns.append({"speaker": speaker, "text": sentence})
        else:
            for sentence in split_sentences(line):
                turns.append({"speaker": None, "text": sentence})

    duration = round(time.perf_counter() - start, 3)

    if not turns:
        logger.error(f"[{rid}] NODE FAILED -> parse_transcript | no sentences parsed | {duration}s")
        return {"turns": [], "error": "No valid sentences could be parsed from the transcript."}

    logger.info(f"[{rid}] NODE END -> parse_transcript | {len(turns)} sentences extracted | {duration}s")
    logger.info(f"[{rid}] parse_transcript OUTPUT:\n{json.dumps(turns, indent=2)}")

    return {"turns": turns}


# =========================================================
# Node 2: sentence_sentiment (LLM call #1)
# =========================================================

def sentence_sentiment_node(state: GraphState) -> Dict[str, Any]:
    rid = state.get("request_id", "unknown")
    if state.get("error"):
        return {}

    start = time.perf_counter()
    turns = state["turns"]
    logger.info(f"[{rid}] NODE START -> sentence_sentiment | {len(turns)} sentences to analyze")

    numbered = "\n".join(
        f"{i + 1}. [{t['speaker'] or 'Unknown'}] {t['text']}" for i, t in enumerate(turns)
    )

    system_prompt = (
        "You are an expert call-center conversation analyst. For each numbered sentence "
        "below, determine its sentiment (Positive, Negative, or Neutral), its primary "
        "emotion (e.g. frustration, satisfaction, anger, confusion, calm, gratitude), "
        "a confidence score between 0.0 and 1.0, and a short one-sentence reasoning. "
        "You MUST return exactly one result per input sentence, in the exact same order. "
        "The number of results must match the number of input sentences."
    )
    human_prompt = f"Sentences:\n{numbered}"

    logger.info(f"[{rid}] LLM CALL #1 (sentence_sentiment) PROMPT:\n{human_prompt}")

    llm = get_llm(temperature=0)
    structured_llm = llm.with_structured_output(SentenceListLLMOutput)

    try:
        parsed: SentenceListLLMOutput = structured_llm.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[{rid}] LLM CALL #1 FAILED (sentence_sentiment): {exc}")
        return {"error": f"LLM sentiment analysis failed: {exc}"}

    duration = round(time.perf_counter() - start, 3)
    raw_dump = [r.model_dump() for r in parsed.results]
    logger.info(
        f"[{rid}] LLM CALL #1 RESPONSE (sentence_sentiment) | "
        f"{len(raw_dump)} results | {duration}s\n{json.dumps(raw_dump, indent=2)}"
    )

    llm_results = parsed.results
    sentence_results: List[Dict[str, Any]] = []

    for i, turn in enumerate(turns):
        if i < len(llm_results):
            r = llm_results[i]
            sentence_results.append(
                {
                    "text": turn["text"],
                    "speaker": turn["speaker"],
                    "sentiment": r.sentiment,
                    "emotion": r.emotion,
                    "confidence": r.confidence,
                    "reasoning": r.reasoning,
                }
            )
        else:
            logger.warning(
                f"[{rid}] sentence_sentiment: missing LLM result for sentence #{i+1}, using fallback"
            )
            sentence_results.append(
                {
                    "text": turn["text"],
                    "speaker": turn["speaker"],
                    "sentiment": "Neutral",
                    "emotion": "unknown",
                    "confidence": 0.5,
                    "reasoning": "No analysis returned by the model for this sentence.",
                }
            )

    logger.info(f"[{rid}] NODE END -> sentence_sentiment | {duration}s")

    return {"sentence_results": sentence_results}


# =========================================================
# Node 3: aggregate_overall (pure computation, no LLM)
# =========================================================

def aggregate_overall_node(state: GraphState) -> Dict[str, Any]:
    rid = state.get("request_id", "unknown")
    if state.get("error"):
        return {}

    start = time.perf_counter()
    logger.info(f"[{rid}] NODE START -> aggregate_overall")

    results = state["sentence_results"]
    if not results:
        logger.warning(f"[{rid}] aggregate_overall: no sentence results, defaulting to Neutral")
        return {"overall_sentiment": "Neutral", "overall_confidence": 0.0}

    score_map = {"Positive": 1, "Neutral": 0, "Negative": -1}
    weighted_sum = sum(score_map[r["sentiment"]] * r["confidence"] for r in results)
    total_confidence = sum(r["confidence"] for r in results) or 1.0
    avg_score = weighted_sum / total_confidence

    if avg_score > 0.15:
        overall = "Positive"
    elif avg_score < -0.15:
        overall = "Negative"
    else:
        overall = "Neutral"

    overall_confidence = round(sum(r["confidence"] for r in results) / len(results), 3)
    duration = round(time.perf_counter() - start, 3)

    logger.info(
        f"[{rid}] NODE END -> aggregate_overall | overall_sentiment={overall} "
        f"avg_score={round(avg_score, 3)} confidence={overall_confidence} | {duration}s"
    )

    return {"overall_sentiment": overall, "overall_confidence": overall_confidence}


# =========================================================
# Node 4: kpi_extraction (LLM call #2)
# =========================================================

def kpi_extraction_node(state: GraphState) -> Dict[str, Any]:
    rid = state.get("request_id", "unknown")
    if state.get("error"):
        return {}

    start = time.perf_counter()
    logger.info(f"[{rid}] NODE START -> kpi_extraction")

    turns = state["turns"]
    transcript_text = "\n".join(
        f"{(t['speaker'] or 'Unknown')}: {t['text']}" for t in turns
    )
    sentiment_summary = "\n".join(
        f"- ({r['speaker'] or 'Unknown'}) {r['sentiment']}/{r['emotion']}: {r['text']}"
        for r in state["sentence_results"]
    )

    system_prompt = (
        "You are a call-center quality assurance analyst. Based on the transcript and "
        "the sentence-level sentiment analysis provided, extract objective call-center KPIs."
    )
    human_prompt = (
        f"TRANSCRIPT:\n{transcript_text}\n\n"
        f"SENTENCE-LEVEL SENTIMENT:\n{sentiment_summary}\n\n"
        "Provide:\n"
        "- csat_score_estimate: estimated customer satisfaction score (0-10)\n"
        "- escalation_risk: Low, Medium, or High\n"
        "- resolution_status: Resolved, Unresolved, or Follow-up needed\n"
        "- agent_sentiment_avg: short phrase describing the agent's average tone\n"
        "- customer_sentiment_avg: short phrase describing the customer's average tone\n"
        "- sentiment_trend: Improving, Worsening, or Stable (comparing start vs end of call)\n"
        "- politeness_score: how polite/professional the agent was (0-10)\n"
        "- key_topics: up to 5 short topic keywords/phrases discussed in the call"
    )

    logger.info(f"[{rid}] LLM CALL #2 (kpi_extraction) PROMPT:\n{human_prompt}")

    llm = get_llm(temperature=0)
    structured_llm = llm.with_structured_output(KPILLMOutput)

    try:
        parsed: KPILLMOutput = structured_llm.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[{rid}] LLM CALL #2 FAILED (kpi_extraction): {exc}")
        return {"error": f"LLM KPI extraction failed: {exc}"}

    duration = round(time.perf_counter() - start, 3)
    kpi_dump = parsed.model_dump()
    logger.info(
        f"[{rid}] LLM CALL #2 RESPONSE (kpi_extraction) | {duration}s\n"
        f"{json.dumps(kpi_dump, indent=2)}"
    )

    logger.info(f"[{rid}] NODE END -> kpi_extraction | {duration}s")

    return {"kpis": kpi_dump}


# =========================================================
# Node 5: summary_node (LLM call #3)
# =========================================================

def summary_node(state: GraphState) -> Dict[str, Any]:
    rid = state.get("request_id", "unknown")
    if state.get("error"):
        return {}

    start = time.perf_counter()
    logger.info(f"[{rid}] NODE START -> summary_node")

    turns = state["turns"]
    transcript_text = "\n".join(
        f"{(t['speaker'] or 'Unknown')}: {t['text']}" for t in turns
    )

    llm = get_llm(temperature=0.3)
    human_prompt = (
        "Summarize the following call transcript in 2-3 sentences, "
        "covering the customer's issue, what the agent did, and the outcome:\n\n"
        f"{transcript_text}"
    )

    logger.info(f"[{rid}] LLM CALL #3 (summary_node) PROMPT:\n{human_prompt}")

    try:
        response = llm.invoke(
            [
                SystemMessage(
                    content="You summarize call-center conversations concisely and factually."
                ),
                HumanMessage(content=human_prompt),
            ]
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[{rid}] LLM CALL #3 FAILED (summary_node): {exc}")
        return {"error": f"LLM summary generation failed: {exc}"}

    duration = round(time.perf_counter() - start, 3)
    summary_text = response.content.strip()

    logger.info(
        f"[{rid}] LLM CALL #3 RESPONSE (summary_node) | {duration}s\nSUMMARY: {summary_text}"
    )
    logger.info(f"[{rid}] NODE END -> summary_node | {duration}s")

    return {"summary": summary_text}


# =========================================================
# Graph Construction
# =========================================================

def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("parse_transcript", parse_transcript_node)
    graph.add_node("sentence_sentiment", sentence_sentiment_node)
    graph.add_node("aggregate_overall", aggregate_overall_node)
    graph.add_node("kpi_extraction", kpi_extraction_node)
    graph.add_node("summary_node", summary_node)

    graph.add_edge(START, "parse_transcript")
    graph.add_edge("parse_transcript", "sentence_sentiment")
    graph.add_edge("sentence_sentiment", "aggregate_overall")
    graph.add_edge("aggregate_overall", "kpi_extraction")
    graph.add_edge("kpi_extraction", "summary_node")
    graph.add_edge("summary_node", END)

    return graph.compile()


compiled_graph = build_graph()