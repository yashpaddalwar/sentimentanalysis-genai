import os
import re
import time
from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from logger_config import get_logger
from models import KPILLMOutput, SentenceListLLMOutput

logger = get_logger("langgraph_pipeline")

MAX_ANALYSIS_UNITS = int(os.getenv("MAX_ANALYSIS_UNITS", "120"))


# =========================================================
# LLM Provider
# =========================================================

def get_llm(temperature: float = 0.0):
    provider = os.getenv("LLM_PROVIDER", "groq").lower()

    if provider == "groq":
        from langchain_groq import ChatGroq

        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not configured.")

        return ChatGroq(
            model=os.getenv(
                "GROQ_MODEL",
                "llama-3.3-70b-versatile",
            ),
            temperature=temperature,
            api_key=api_key,
        )

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured."
            )

        return ChatGoogleGenerativeAI(
            model=os.getenv(
                "GEMINI_MODEL",
                "gemini-1.5-flash",
            ),
            temperature=temperature,
            google_api_key=api_key,
        )

    raise ValueError(
        f"Unsupported LLM_PROVIDER: {provider}"
    )


# =========================================================
# LangGraph State
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
# Transcript parsing
# =========================================================

# Handles:
# Agent:
# Customer:
# Agent -
# Customer -
# [Agent]:
# [Customer]:
# AGENT:
# CUSTOMER:
#
# The parser intentionally does NOT require the speaker to be
# exactly "Agent" or "Customer", because transcripts can contain
# names such as "Rahul", "Support Executive", etc.
SPEAKER_LINE_RE = re.compile(
    r"""
    ^\s*
    (?:\[(?P<bracket>[^\]]{1,40})\]|(?P<plain>[A-Za-z][A-Za-z0-9 _/&\-]{0,39}))
    \s*(?::|-)\s*
    (?P<text>.+?)\s*$
    """,
    re.VERBOSE,
)

# Timestamp prefixes that frequently appear in call transcripts.
TIMESTAMP_RE = re.compile(
    r"""
    ^\s*
    (?:
        \[\d{1,2}:\d{2}(?::\d{2})?\]
        |
        \d{1,2}:\d{2}(?::\d{2})?
        |
        \d{1,2}:\d{2}(?:\s*[APMapm]{2})
    )
    \s*[-:|]?\s*
    """,
    re.VERBOSE,
)

# Used only for actual sentence boundaries. This is deliberately
# conservative because transcripts contain abbreviations, decimals,
# names, URLs, etc.
SENTENCE_BOUNDARY_RE = re.compile(
    r"(?<=[.!?।])\s+(?=[A-Z0-9\u0900-\u097F])"
)


def clean_line(line: str) -> str:
    line = line.replace("\x00", "")
    line = TIMESTAMP_RE.sub("", line.strip())

    # Remove excessive whitespace while keeping the actual content.
    line = re.sub(r"[ \t]+", " ", line)

    return line.strip()


def parse_speaker(line: str) -> tuple[Optional[str], Optional[str]]:
    match = SPEAKER_LINE_RE.match(line)

    if not match:
        return None, None

    speaker = (
        match.group("bracket")
        or match.group("plain")
        or ""
    ).strip()

    text = match.group("text").strip()

    if not speaker or not text:
        return None, None

    return speaker, text


def smart_split_text(text: str) -> List[str]:
    """
    Split an utterance into analysis units without aggressively
    fragmenting natural conversational text.

    Important:
    We prefer one short utterance over dozens of artificial fragments.
    """

    text = re.sub(r"\s+", " ", text.strip())

    if not text:
        return []

    # If punctuation exists, use conservative sentence boundaries.
    pieces = SENTENCE_BOUNDARY_RE.split(text)

    cleaned = [
        piece.strip()
        for piece in pieces
        if piece.strip()
    ]

    # If nothing useful was split, retain the full utterance.
    return cleaned or [text]


def parse_transcript(
    raw_text: str,
) -> List[Dict[str, Optional[str]]]:
    """
    Smart parser for imperfect real-world transcripts.

    Strategy:
    - detect speaker labels when available
    - preserve continuation lines
    - remove timestamps
    - split only at conservative sentence boundaries
    - preserve speaker identity
    """

    lines = [
        clean_line(line)
        for line in raw_text.splitlines()
        if line.strip()
    ]

    turns: List[Dict[str, Optional[str]]] = []

    current_speaker: Optional[str] = None
    current_text_parts: List[str] = []

    def flush_current_turn() -> None:
        nonlocal current_text_parts

        if not current_text_parts:
            return

        combined_text = " ".join(
            part.strip()
            for part in current_text_parts
            if part.strip()
        ).strip()

        if not combined_text:
            current_text_parts = []
            return

        for sentence in smart_split_text(
            combined_text
        ):
            turns.append(
                {
                    "speaker": current_speaker,
                    "text": sentence,
                }
            )

        current_text_parts = []

    for line in lines:
        speaker, text = parse_speaker(line)

        if speaker is not None:
            # New speaker = finish the previous utterance.
            flush_current_turn()

            current_speaker = speaker
            current_text_parts = [text]

        else:
            # Continuation line.
            current_text_parts.append(line)

    flush_current_turn()

    return turns


# =========================================================
# Normalization helpers
# =========================================================

def normalize_sentiment(value: str) -> str:
    """
    Convert model drift such as:
        surprised
        happy
        angry
        mixed
    into the contractual API labels.
    """

    normalized = (
        str(value)
        .strip()
        .lower()
    )

    if normalized in {
        "positive",
        "pos",
        "good",
        "happy",
        "satisfied",
        "grateful",
        "relieved",
    }:
        return "Positive"

    if normalized in {
        "negative",
        "neg",
        "bad",
        "angry",
        "frustrated",
        "upset",
        "dissatisfied",
        "sad",
    }:
        return "Negative"

    # Surprise, confusion and politeness are not inherently
    # positive or negative.
    return "Neutral"


def normalize_emotion(value: str) -> str:
    value = str(value).strip()

    return value[:60] if value else "neutral"


def normalize_reasoning(value: str) -> str:
    value = re.sub(
        r"\s+",
        " ",
        str(value).strip(),
    )

    return value[:220] if value else "No reasoning provided."


# =========================================================
# Node 1: parse_transcript
# =========================================================

def parse_transcript_node(
    state: GraphState,
) -> Dict[str, Any]:

    rid = state.get(
        "request_id",
        "unknown",
    )

    start = time.perf_counter()

    logger.info(
        f"[{rid}] NODE START -> parse_transcript"
    )

    try:
        turns = parse_transcript(
            state["raw_text"]
        )
    except Exception:
        logger.exception(
            f"[{rid}] Transcript parsing failed"
        )

        return {
            "turns": [],
            "error": "Unable to parse the transcript.",
        }

    duration = round(
        time.perf_counter() - start,
        3,
    )

    if not turns:
        return {
            "turns": [],
            "error": (
                "No usable conversational content "
                "was found in the transcript."
            ),
        }

    if len(turns) > MAX_ANALYSIS_UNITS:
        logger.warning(
            f"[{rid}] Analysis unit count "
            f"{len(turns)} exceeds limit "
            f"{MAX_ANALYSIS_UNITS}"
        )

        return {
            "turns": [],
            "error": (
                f"Transcript is too granular for analysis. "
                f"Please provide a transcript with fewer than "
                f"{MAX_ANALYSIS_UNITS} analysis units."
            ),
        }

    labeled = sum(
        1
        for turn in turns
        if turn["speaker"]
    )

    logger.info(
        f"[{rid}] NODE END -> parse_transcript | "
        f"analysis_units={len(turns)} "
        f"labeled={labeled} | {duration}s"
    )

    return {
        "turns": turns
    }


# =========================================================
# Node 2: sentence_sentiment
# LLM call #1
# =========================================================

def sentence_sentiment_node(
    state: GraphState,
) -> Dict[str, Any]:

    rid = state.get(
        "request_id",
        "unknown",
    )

    if state.get("error"):
        return {}

    start = time.perf_counter()

    turns = state["turns"]

    logger.info(
        f"[{rid}] NODE START -> sentence_sentiment | "
        f"units={len(turns)}"
    )

    numbered = "\n".join(
        (
            f"{index + 1}. "
            f"[{turn['speaker'] or 'Unknown'}] "
            f"{turn['text']}"
        )
        for index, turn in enumerate(turns)
    )

    system_prompt = """
You are an expert call-center conversation analyst.

Analyze every numbered conversational unit.

For each unit return:
- sentiment: Positive, Negative, or Neutral
- emotion: one concise primary emotion
- confidence: 0.0 to 1.0
- reasoning: one very short factual sentence

IMPORTANT:
- "Surprised", "Confused", "Polite", "Urgent", etc.
  are EMOTIONS, not sentiment labels.
- Sentiment MUST be exactly Positive, Negative, or Neutral.
- Surprise alone is Neutral unless the wording itself is
  clearly positive or negative.
- Greeting, acknowledgement, information gathering,
  clarification and farewell are normally Neutral.
- Preserve the input order.
- Return exactly one result per input unit.
- Never invent or omit a unit.
- Keep reasoning concise.
""".strip()

    human_prompt = (
        "CONVERSATIONAL UNITS:\n\n"
        f"{numbered}"
    )

    logger.info(
        f"[{rid}] LLM CALL #1 START -> sentence_sentiment"
    )

    try:
        llm = get_llm(temperature=0)

        structured_llm = llm.with_structured_output(
            SentenceListLLMOutput
        )

        parsed: SentenceListLLMOutput = (
            structured_llm.invoke(
                [
                    SystemMessage(
                        content=system_prompt
                    ),
                    HumanMessage(
                        content=human_prompt
                    ),
                ]
            )
        )

    except Exception:
        logger.exception(
            f"[{rid}] LLM CALL #1 FAILED -> "
            f"sentence_sentiment"
        )

        return {
            "error": (
                "Sentence-level sentiment analysis "
                "failed. The model could not return "
                "a valid analysis."
            )
        }

    results = parsed.results

    # NEVER silently align mismatched results.
    if len(results) != len(turns):
        logger.error(
            f"[{rid}] LLM CALL #1 INVALID COUNT | "
            f"expected={len(turns)} "
            f"received={len(results)}"
        )

        return {
            "error": (
                "The sentiment model returned an "
                "incomplete analysis."
            )
        }

    sentence_results: List[
        Dict[str, Any]
    ] = []

    for turn, result in zip(
        turns,
        results,
    ):
        sentence_results.append(
            {
                "text": turn["text"],
                "speaker": turn["speaker"],
                "sentiment": normalize_sentiment(
                    result.sentiment
                ),
                "emotion": normalize_emotion(
                    result.emotion
                ),
                "confidence": max(
                    0.0,
                    min(
                        1.0,
                        float(
                            result.confidence
                        ),
                    ),
                ),
                "reasoning": normalize_reasoning(
                    result.reasoning
                ),
            }
        )

    duration = round(
        time.perf_counter() - start,
        3,
    )

    logger.info(
        f"[{rid}] LLM CALL #1 END -> "
        f"sentence_sentiment | "
        f"results={len(sentence_results)} | "
        f"{duration}s"
    )

    return {
        "sentence_results": sentence_results
    }


# =========================================================
# Node 3: aggregate_overall
# Pure Python — no LLM
# =========================================================

def aggregate_overall_node(
    state: GraphState,
) -> Dict[str, Any]:

    rid = state.get(
        "request_id",
        "unknown",
    )

    if state.get("error"):
        return {}

    results = state[
        "sentence_results"
    ]

    if not results:
        return {
            "overall_sentiment": "Neutral",
            "overall_confidence": 0.0,
        }

    score_map = {
        "Positive": 1.0,
        "Neutral": 0.0,
        "Negative": -1.0,
    }

    weighted_sum = sum(
        score_map[
            result["sentiment"]
        ]
        * result["confidence"]
        for result in results
    )

    total_confidence = (
        sum(
            result["confidence"]
            for result in results
        )
        or 1.0
    )

    average_score = (
        weighted_sum
        / total_confidence
    )

    if average_score > 0.15:
        sentiment = "Positive"
    elif average_score < -0.15:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"

    confidence = round(
        sum(
            result["confidence"]
            for result in results
        )
        / len(results),
        3,
    )

    logger.info(
        f"[{rid}] NODE END -> "
        f"aggregate_overall | "
        f"sentiment={sentiment} "
        f"confidence={confidence}"
    )

    return {
        "overall_sentiment": sentiment,
        "overall_confidence": confidence,
    }


# =========================================================
# Node 4: KPI extraction
# LLM call #2
# =========================================================

def kpi_extraction_node(
    state: GraphState,
) -> Dict[str, Any]:

    rid = state.get(
        "request_id",
        "unknown",
    )

    if state.get("error"):
        return {}

    turns = state["turns"]

    transcript_text = "\n".join(
        f"{turn['speaker'] or 'Unknown'}: "
        f"{turn['text']}"
        for turn in turns
    )

    sentiment_summary = "\n".join(
        (
            f"- "
            f"{result['speaker'] or 'Unknown'} | "
            f"{result['sentiment']} | "
            f"{result['emotion']} | "
            f"{result['text']}"
        )
        for result in state[
            "sentence_results"
        ]
    )

    system_prompt = """
You are a call-center quality analyst.

Based only on the transcript and sentence-level
analysis, extract objective call KPIs.

Do not invent facts.
Be conservative when evidence is ambiguous.
""".strip()

    human_prompt = f"""
TRANSCRIPT:
{transcript_text}

SENTIMENT ANALYSIS:
{sentiment_summary}

Return:
- csat_score_estimate: 0-10
- escalation_risk: Low | Medium | High
- resolution_status: Resolved | Unresolved | Follow-up needed
- agent_sentiment_avg
- customer_sentiment_avg
- sentiment_trend: Improving | Worsening | Stable
- politeness_score: 0-10
- key_topics: maximum 5
""".strip()

    try:
        llm = get_llm(temperature=0)

        structured_llm = llm.with_structured_output(
            KPILLMOutput
        )

        parsed: KPILLMOutput = (
            structured_llm.invoke(
                [
                    SystemMessage(
                        content=system_prompt
                    ),
                    HumanMessage(
                        content=human_prompt
                    ),
                ]
            )
        )

    except Exception:
        logger.exception(
            f"[{rid}] LLM CALL #2 FAILED -> "
            f"kpi_extraction"
        )

        return {
            "error": "KPI extraction failed."
        }

    return {
        "kpis": parsed.model_dump()
    }


# =========================================================
# Node 5: summary
# LLM call #3
# =========================================================

def summary_node(
    state: GraphState,
) -> Dict[str, Any]:

    rid = state.get(
        "request_id",
        "unknown",
    )

    if state.get("error"):
        return {}

    transcript_text = "\n".join(
        f"{turn['speaker'] or 'Unknown'}: "
        f"{turn['text']}"
        for turn in state["turns"]
    )

    system_prompt = """
You are a professional call-center summarizer.

Write a factual 2-3 sentence summary covering:
1. customer's issue
2. agent's action
3. outcome

Do not invent information.
""".strip()

    try:
        llm = get_llm(
            temperature=0.2
        )

        response = llm.invoke(
            [
                SystemMessage(
                    content=system_prompt
                ),
                HumanMessage(
                    content=(
                        "CALL TRANSCRIPT:\n"
                        f"{transcript_text}"
                    ),
                ),
            ]
        )

    except Exception:
        logger.exception(
            f"[{rid}] LLM CALL #3 FAILED -> summary"
        )

        return {
            "error": "Call summary generation failed."
        }

    summary = (
        response.content
        .strip()
    )

    if not summary:
        return {
            "error": "The summary model returned an empty response."
        }

    return {
        "summary": summary
    }


# =========================================================
# Graph
# =========================================================

def build_graph():
    graph = StateGraph(
        GraphState
    )

    graph.add_node(
        "parse_transcript",
        parse_transcript_node,
    )

    graph.add_node(
        "sentence_sentiment",
        sentence_sentiment_node,
    )

    graph.add_node(
        "aggregate_overall",
        aggregate_overall_node,
    )

    graph.add_node(
        "kpi_extraction",
        kpi_extraction_node,
    )

    graph.add_node(
        "summary_node",
        summary_node,
    )

    graph.add_edge(
        START,
        "parse_transcript",
    )

    graph.add_edge(
        "parse_transcript",
        "sentence_sentiment",
    )

    graph.add_edge(
        "sentence_sentiment",
        "aggregate_overall",
    )

    # Independent branches.
    graph.add_edge(
        "aggregate_overall",
        "kpi_extraction",
    )

    graph.add_edge(
        "aggregate_overall",
        "summary_node",
    )

    graph.add_edge(
        "kpi_extraction",
        END,
    )

    graph.add_edge(
        "summary_node",
        END,
    )

    return graph.compile()


compiled_graph = build_graph()