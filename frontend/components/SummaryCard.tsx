import { Sentiment } from "@/types";

interface SummaryCardProps {
  overallSentiment: Sentiment;
  overallConfidence: number;
  summary: string;
}

const sentimentStyles: Record<Sentiment, string> = {
  Positive: "bg-green-100 text-green-700 border-green-300",
  Negative: "bg-red-100 text-red-700 border-red-300",
  Neutral: "bg-gray-100 text-gray-700 border-gray-300",
};

export default function SummaryCard({
  overallSentiment,
  overallConfidence,
  summary,
}: SummaryCardProps) {
  return (
    <div className="rounded-2xl bg-white p-6 shadow-md">
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <span
          className={`rounded-full border px-4 py-1 text-sm font-semibold ${sentimentStyles[overallSentiment]}`}
        >
          {overallSentiment}
        </span>
        <span className="text-sm text-gray-500">
          Confidence: {(overallConfidence * 100).toFixed(0)}%
        </span>
      </div>
      <h2 className="mb-1 text-lg font-semibold text-gray-900">Call Summary</h2>
      <p className="leading-relaxed text-gray-600">{summary}</p>
    </div>
  );
}