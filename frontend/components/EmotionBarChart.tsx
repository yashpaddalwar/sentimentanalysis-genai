"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { SentenceAnalysis } from "@/types";

export default function EmotionBarChart({
  sentences,
}: {
  sentences: SentenceAnalysis[];
}) {
  const counts: Record<string, number> = {};
  sentences.forEach((s) => {
    counts[s.emotion] = (counts[s.emotion] || 0) + 1;
  });
  const data = Object.entries(counts)
    .map(([emotion, count]) => ({ emotion, count }))
    .sort((a, b) => b.count - a.count);

  return (
    <div className="rounded-2xl bg-white p-6 shadow-md">
      <h3 className="mb-4 text-base font-semibold text-gray-900">Emotions Detected</h3>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="emotion" interval={0} angle={-20} textAnchor="end" height={60} />
          <YAxis allowDecimals={false} />
          <Tooltip />
          <Bar dataKey="count" fill="#7c3aed" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}