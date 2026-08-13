"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  isAuthenticated,
  logout,
} from "@/lib/auth";

import {
  analyzeTranscript,
} from "@/lib/api";

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

  const [authChecked, setAuthChecked] =
    useState(false);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] = useState("");

  const [result, setResult] =
    useState<AnalysisResponse | null>(null);

  const [fileName, setFileName] =
    useState("");

  useEffect(() => {
    let mounted = true;

    async function checkAuth() {
      const authenticated =
        await isAuthenticated();

      if (!mounted) return;

      if (!authenticated) {
        router.replace("/login");
        return;
      }

      setAuthChecked(true);
    }

    checkAuth();

    return () => {
      mounted = false;
    };
  }, [router]);

  async function handleAnalyze(file: File) {
    setLoading(true);
    setError("");
    setResult(null);
    setFileName(file.name);

    try {
      const data =
        await analyzeTranscript(file);

      setResult(data);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Something went wrong.";

      setError(message);

      if (
        message
          .toLowerCase()
          .includes("session")
      ) {
        logout();
        router.replace("/login");
      }
    } finally {
      setLoading(false);
    }
  }

  function handleLogout() {
    logout();
    router.replace("/login");
  }

  function handleDownloadJson() {
    if (!result) return;

    const blob = new Blob(
      [JSON.stringify(result, null, 2)],
      {
        type: "application/json",
      }
    );

    const url =
      URL.createObjectURL(blob);

    const anchor =
      document.createElement("a");

    anchor.href = url;
    anchor.download = `${
      fileName
        .replace(/\.txt$/i, "")
        .replace(/[^a-z0-9_-]/gi, "_") ||
      "call-analysis"
    }-analysis.json`;

    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();

    URL.revokeObjectURL(url);
  }

  if (!authChecked) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-gray-500">
          Checking session...
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-16">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
          <div>
            <h1 className="text-xl font-bold text-gray-900">
              📞 Call Sentiment Analyzer
            </h1>

            <p className="mt-1 hidden text-xs text-gray-500 sm:block">
              LangGraph-powered call intelligence dashboard
            </p>
          </div>

          <button
            onClick={handleLogout}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-100"
          >
            Logout
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
        <UploadZone
          onAnalyze={handleAnalyze}
          loading={loading}
        />

        {error && (
          <div
            role="alert"
            className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          >
            {error}
          </div>
        )}

        {result && (
          <div className="space-y-6">
            <div className="flex flex-col gap-3 rounded-2xl bg-white p-4 shadow-md sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
                  Analyzed file
                </p>

                <p className="mt-1 truncate font-semibold text-gray-800">
                  {fileName}
                </p>
              </div>

              <button
                onClick={handleDownloadJson}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-50"
              >
                Download JSON
              </button>
            </div>

            <SummaryCard
              overallSentiment={
                result.overall_sentiment
              }
              overallConfidence={
                result.overall_confidence
              }
              summary={result.summary}
            />

            <KpiGrid kpis={result.kpis} />

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <SentimentPieChart
                sentences={result.sentences}
              />

              <EmotionBarChart
                sentences={result.sentences}
              />
            </div>

            <SentimentTrendChart
              sentences={result.sentences}
            />

            <SentenceTable
              sentences={result.sentences}
            />
          </div>
        )}
      </main>
    </div>
  );
}