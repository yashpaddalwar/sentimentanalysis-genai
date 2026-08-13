"use client";

import { Fragment, useState } from "react";
import { SentenceAnalysis } from "@/types";

const badgeStyles: Record<string, string> = {
  Positive: "bg-green-100 text-green-700",
  Negative: "bg-red-100 text-red-700",
  Neutral: "bg-gray-100 text-gray-700",
};

export default function SentenceTable({
  sentences,
}: {
  sentences: SentenceAnalysis[];
}) {
  const [expanded, setExpanded] = useState<number | null>(null);

  return (
    <div className="rounded-2xl bg-white p-6 shadow-md">
      <h3 className="mb-4 text-base font-semibold text-gray-900">
        Sentence-by-Sentence Analysis
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[600px] table-auto border-collapse text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs uppercase tracking-wide text-gray-400">
              <th className="py-2 pr-4">#</th>
              <th className="py-2 pr-4">Speaker</th>
              <th className="py-2 pr-4">Sentence</th>
              <th className="py-2 pr-4">Sentiment</th>
              <th className="py-2 pr-4">Emotion</th>
              <th className="py-2 pr-4"></th>
            </tr>
          </thead>
          <tbody>
            {sentences.map((s, idx) => (
              <Fragment key={idx}>
                <tr
                  className="cursor-pointer border-b border-gray-100 hover:bg-gray-50"
                  onClick={() => setExpanded(expanded === idx ? null : idx)}
                >
                  <td className="py-2 pr-4 align-top text-gray-400">{idx + 1}</td>
                  <td className="py-2 pr-4 align-top font-medium text-gray-700">
                    {s.speaker || "—"}
                  </td>
                  <td className="py-2 pr-4 align-top text-gray-700">{s.text}</td>
                  <td className="py-2 pr-4 align-top">
                    <span
                      className={`rounded-full px-2 py-1 text-xs font-semibold ${badgeStyles[s.sentiment]}`}
                    >
                      {s.sentiment}
                    </span>
                  </td>
                  <td className="py-2 pr-4 align-top capitalize text-gray-600">
                    {s.emotion}
                  </td>
                  <td className="py-2 pr-4 align-top text-blue-600">
                    {expanded === idx ? "Hide" : "Details"}
                  </td>
                </tr>
                {expanded === idx && (
                  <tr className="bg-blue-50/50">
                    <td colSpan={6} className="px-4 py-3 text-sm text-gray-600">
                      <span className="font-semibold text-gray-800">Reasoning: </span>
                      {s.reasoning}
                      <span className="ml-4 font-semibold text-gray-800">Confidence: </span>
                      {(s.confidence * 100).toFixed(0)}%
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}