"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isAuthenticated, logout } from "@/lib/auth";
import { analyzeTranscript } from "@/lib/api";
import { AnalysisResponse } from "@/types";
import UploadZone from "@/components/UploadZone";
import SummaryCard from "@/components/SummaryCard";
import SentimentPieChart from "@/components/SentimentPieChart";
import SentimentTrendChart from "@/components/SentimentTrendChart";
import EmotionBarChart from "@/components/EmotionBarChart";
import KpiGrid from "@/components/KpiGrid";
import SentenceTable from "@/components/SentenceTable";

export default function DashboardPage() {
  const router = useRouter();
  const [authChecked, setAuthChecked] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AnalysisResponse | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
    } else {
      setAuthChecked(true);
    }
  }, [router]);

  async function handleAnalyze(file: File) {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await analyzeTranscript(file);
      setResult(data);
    } catch (err: any) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  function handleLogout() {
    logout();
    router.replace("/login");
  }

  if (!authChecked) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-gray-500">Checking session...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-16">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <h1 className="text-xl font-bold text-gray-900">
            📞 Call Sentiment Analyzer
          </h1>
          <button
            onClick={handleLogout}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100"
          >
            Logout
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
        <UploadZone onAnalyze={handleAnalyze} loading={loading} />

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
            {error}
          </div>
        )}

        {result && (
          <div className="space-y-6">
            <SummaryCard
              overallSentiment={result.overall_sentiment}
              overallConfidence={result.overall_confidence}
              summary={result.summary}
            />

            <KpiGrid kpis={result.kpis} />

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <SentimentPieChart sentences={result.sentences} />
              <EmotionBarChart sentences={result.sentences} />
            </div>

            <SentimentTrendChart sentences={result.sentences} />

            <SentenceTable sentences={result.sentences} />
          </div>
        )}
      </main>
    </div>
  );
}