import { KPIs } from "@/types";

function riskColor(risk: string) {
  if (risk === "Low") return "bg-green-50 text-green-700 border-green-200";
  if (risk === "Medium") return "bg-yellow-50 text-yellow-700 border-yellow-200";
  return "bg-red-50 text-red-700 border-red-200";
}

function resolutionColor(status: string) {
  if (status === "Resolved") return "bg-green-50 text-green-700 border-green-200";
  if (status === "Follow-up needed") return "bg-yellow-50 text-yellow-700 border-yellow-200";
  return "bg-red-50 text-red-700 border-red-200";
}

function scoreColor(score: number) {
  if (score >= 7) return "text-green-600";
  if (score >= 4) return "text-yellow-600";
  return "text-red-600";
}

function trendColor(trend: string) {
  if (trend === "Improving") return "bg-green-50 text-green-700 border-green-200";
  if (trend === "Stable") return "bg-gray-50 text-gray-700 border-gray-200";
  return "bg-red-50 text-red-700 border-red-200";
}

export default function KpiGrid({ kpis }: { kpis: KPIs }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div className="rounded-2xl bg-white p-5 shadow-md">
        <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
          CSAT Score Estimate
        </p>
        <p className={`mt-2 text-3xl font-bold ${scoreColor(kpis.csat_score_estimate)}`}>
          {kpis.csat_score_estimate.toFixed(1)}/10
        </p>
      </div>

      <div className="rounded-2xl bg-white p-5 shadow-md">
        <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
          Politeness Score
        </p>
        <p className={`mt-2 text-3xl font-bold ${scoreColor(kpis.politeness_score)}`}>
          {kpis.politeness_score.toFixed(1)}/10
        </p>
      </div>

      <div className="rounded-2xl bg-white p-5 shadow-md">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-400">
          Escalation Risk
        </p>
        <span
          className={`inline-block rounded-full border px-3 py-1 text-sm font-semibold ${riskColor(
            kpis.escalation_risk
          )}`}
        >
          {kpis.escalation_risk}
        </span>
      </div>

      <div className="rounded-2xl bg-white p-5 shadow-md">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-400">
          Resolution Status
        </p>
        <span
          className={`inline-block rounded-full border px-3 py-1 text-sm font-semibold ${resolutionColor(
            kpis.resolution_status
          )}`}
        >
          {kpis.resolution_status}
        </span>
      </div>

      <div className="rounded-2xl bg-white p-5 shadow-md">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-400">
          Sentiment Trend
        </p>
        <span
          className={`inline-block rounded-full border px-3 py-1 text-sm font-semibold ${trendColor(
            kpis.sentiment_trend
          )}`}
        >
          {kpis.sentiment_trend}
        </span>
      </div>

      <div className="rounded-2xl bg-white p-5 shadow-md">
        <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
          Agent Sentiment Avg
        </p>
        <p className="mt-2 text-sm font-semibold text-gray-800">
          {kpis.agent_sentiment_avg}
        </p>
      </div>

      <div className="rounded-2xl bg-white p-5 shadow-md">
        <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
          Customer Sentiment Avg
        </p>
        <p className="mt-2 text-sm font-semibold text-gray-800">
          {kpis.customer_sentiment_avg}
        </p>
      </div>

      <div className="rounded-2xl bg-white p-5 shadow-md sm:col-span-2 lg:col-span-1">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-400">
          Key Topics
        </p>
        <div className="flex flex-wrap gap-2">
          {kpis.key_topics.map((topic) => (
            <span
              key={topic}
              className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700"
            >
              {topic}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}