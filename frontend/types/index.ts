export type Sentiment = "Positive" | "Negative" | "Neutral";

export interface SentenceAnalysis {
  text: string;
  speaker: string | null;
  sentiment: Sentiment;
  emotion: string;
  confidence: number;
  reasoning: string;
}

export interface KPIs {
  csat_score_estimate: number;
  escalation_risk: "Low" | "Medium" | "High";
  resolution_status: "Resolved" | "Unresolved" | "Follow-up needed";
  agent_sentiment_avg: string;
  customer_sentiment_avg: string;
  sentiment_trend: "Improving" | "Worsening" | "Stable";
  politeness_score: number;
  key_topics: string[];
}

export interface AnalysisResponse {
  overall_sentiment: Sentiment;
  overall_confidence: number;
  summary: string;
  sentences: SentenceAnalysis[];
  kpis: KPIs;
}