"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { SentenceAnalysis } from "@/types";

const scoreMap: Record<string, number> = { Positive: 1, Neutral: 0, Negative: -1 };

export default function SentimentTrendChart({
  sentences,
}: {
  sentences: SentenceAnalysis[];
}) {
  const data = sentences.map((s, idx) => ({
    index: idx + 1,
    score: scoreMap[s.sentiment] * s.confidence,
  }));

  return (
    <div className="rounded-2xl bg-white p-6 shadow-md">
      <h3 className="mb-4 text-base font-semibold text-gray-900">
        Sentiment Trend Across Conversation
      </h3>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="index"
            label={{ value: "Sentence #", position: "insideBottom", offset: -5 }}
          />
          <YAxis domain={[-1, 1]} />
          <Tooltip />
          <Line type="monotone" dataKey="score" stroke="#2563eb" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}