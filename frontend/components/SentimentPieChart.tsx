"use client";

import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { SentenceAnalysis } from "@/types";

const COLORS: Record<string, string> = {
  Positive: "#16a34a",
  Negative: "#dc2626",
  Neutral: "#6b7280",
};

export default function SentimentPieChart({
  sentences,
}: {
  sentences: SentenceAnalysis[];
}) {
  const counts = { Positive: 0, Negative: 0, Neutral: 0 };
  sentences.forEach((s) => {
    counts[s.sentiment] += 1;
  });
  const data = Object.entries(counts).map(([name, value]) => ({ name, value }));

  return (
    <div className="rounded-2xl bg-white p-6 shadow-md">
      <h3 className="mb-4 text-base font-semibold text-gray-900">
        Sentiment Distribution
      </h3>
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            innerRadius={60}
            outerRadius={90}
            paddingAngle={3}
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={COLORS[entry.name]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}