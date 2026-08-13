from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# =========================================================
# API Response Schemas (returned by FastAPI /analyze)
# =========================================================

class SentenceAnalysis(BaseModel):
    text: str
    speaker: Optional[str] = None
    sentiment: Literal["Positive", "Negative", "Neutral"]
    emotion: str
    confidence: float
    reasoning: str


class KPIs(BaseModel):
    csat_score_estimate: float = Field(ge=0, le=10)
    escalation_risk: Literal["Low", "Medium", "High"]
    resolution_status: Literal["Resolved", "Unresolved", "Follow-up needed"]
    agent_sentiment_avg: str
    customer_sentiment_avg: str
    sentiment_trend: Literal["Improving", "Worsening", "Stable"]
    politeness_score: float = Field(ge=0, le=10)
    key_topics: List[str]


class AnalysisResponse(BaseModel):
    overall_sentiment: Literal["Positive", "Negative", "Neutral"]
    overall_confidence: float
    summary: str
    sentences: List[SentenceAnalysis]
    kpis: KPIs


class ErrorResponse(BaseModel):
    detail: str


# =========================================================
# Internal LLM Structured-Output Schemas (used inside the
# LangGraph pipeline to force structured JSON from the LLM)
# =========================================================

class SentenceLLMOutput(BaseModel):
    sentiment: Literal["Positive", "Negative", "Neutral"] = Field(
        description="Sentiment of this sentence"
    )
    emotion: str = Field(
        description="Primary emotion, e.g. frustration, joy, confusion, calm, anger, satisfaction"
    )
    confidence: float = Field(ge=0, le=1, description="Confidence score between 0 and 1")
    reasoning: str = Field(description="One short sentence explaining the classification")


class SentenceListLLMOutput(BaseModel):
    results: List[SentenceLLMOutput] = Field(
        description="List of sentiment results, one per input sentence, in the exact same order"
    )


class KPILLMOutput(BaseModel):
    csat_score_estimate: float = Field(ge=0, le=10)
    escalation_risk: Literal["Low", "Medium", "High"]
    resolution_status: Literal["Resolved", "Unresolved", "Follow-up needed"]
    agent_sentiment_avg: str
    customer_sentiment_avg: str
    sentiment_trend: Literal["Improving", "Worsening", "Stable"]
    politeness_score: float = Field(ge=0, le=10)
    key_topics: List[str]