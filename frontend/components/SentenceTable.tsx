"use client";

import {
  Fragment,
  useMemo,
  useState,
} from "react";

import { SentenceAnalysis } from "@/types";

const badgeStyles: Record<
  string,
  string
> = {
  Positive:
    "bg-green-100 text-green-700",
  Negative:
    "bg-red-100 text-red-700",
  Neutral:
    "bg-gray-100 text-gray-700",
};

export default function SentenceTable({
  sentences,
}: {
  sentences: SentenceAnalysis[];
}) {
  const [expanded, setExpanded] =
    useState<number | null>(null);

  const [search, setSearch] =
    useState("");

  const [sentimentFilter, setSentimentFilter] =
    useState<
      "All" | "Positive" | "Negative" | "Neutral"
    >("All");

  const filteredSentences =
    useMemo(() => {
      const normalizedSearch =
        search.trim().toLowerCase();

      return sentences.filter(
        (sentence) => {
          const matchesSearch =
            !normalizedSearch ||
            sentence.text
              .toLowerCase()
              .includes(normalizedSearch) ||
            sentence.emotion
              .toLowerCase()
              .includes(normalizedSearch) ||
            (sentence.speaker ?? "")
              .toLowerCase()
              .includes(normalizedSearch);

          const matchesSentiment =
            sentimentFilter === "All" ||
            sentence.sentiment ===
              sentimentFilter;

          return (
            matchesSearch &&
            matchesSentiment
          );
        }
      );
    }, [
      sentences,
      search,
      sentimentFilter,
    ]);

  return (
    <div className="rounded-2xl bg-white p-6 shadow-md">
      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h3 className="text-base font-semibold text-gray-900">
            Sentence-by-Sentence Analysis
          </h3>

          <p className="mt-1 text-xs text-gray-400">
            {filteredSentences.length} of{" "}
            {sentences.length} sentences shown
          </p>
        </div>

        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            value={search}
            onChange={(event) =>
              setSearch(event.target.value)
            }
            placeholder="Search text, speaker, emotion..."
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />

          <select
            value={sentimentFilter}
            onChange={(event) =>
              setSentimentFilter(
                event.target.value as
                  | "All"
                  | "Positive"
                  | "Negative"
                  | "Neutral"
              )
            }
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blue-500"
          >
            <option value="All">
              All sentiments
            </option>
            <option value="Positive">
              Positive
            </option>
            <option value="Negative">
              Negative
            </option>
            <option value="Neutral">
              Neutral
            </option>
          </select>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[700px] table-auto border-collapse text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs uppercase tracking-wide text-gray-400">
              <th className="py-2 pr-4">
                #
              </th>

              <th className="py-2 pr-4">
                Speaker
              </th>

              <th className="py-2 pr-4">
                Sentence
              </th>

              <th className="py-2 pr-4">
                Sentiment
              </th>

              <th className="py-2 pr-4">
                Emotion
              </th>

              <th className="py-2 pr-4">
              </th>
            </tr>
          </thead>

          <tbody>
            {filteredSentences.map(
              (sentence) => {
                const originalIndex =
                  sentences.indexOf(
                    sentence
                  );

                const isExpanded =
                  expanded === originalIndex;

                return (
                  <Fragment
                    key={originalIndex}
                  >
                    <tr
                      className="cursor-pointer border-b border-gray-100 hover:bg-gray-50"
                      onClick={() =>
                        setExpanded(
                          isExpanded
                            ? null
                            : originalIndex
                        )
                      }
                      aria-expanded={
                        isExpanded
                      }
                    >
                      <td className="py-2 pr-4 align-top text-gray-400">
                        {originalIndex + 1}
                      </td>

                      <td className="py-2 pr-4 align-top font-medium text-gray-700">
                        {sentence.speaker ||
                          "—"}
                      </td>

                      <td className="max-w-md py-2 pr-4 align-top text-gray-700">
                        {sentence.text}
                      </td>

                      <td className="py-2 pr-4 align-top">
                        <span
                          className={`rounded-full px-2 py-1 text-xs font-semibold ${
                            badgeStyles[
                              sentence.sentiment
                            ]
                          }`}
                        >
                          {
                            sentence.sentiment
                          }
                        </span>
                      </td>

                      <td className="py-2 pr-4 align-top capitalize text-gray-600">
                        {sentence.emotion}
                      </td>

                      <td className="py-2 pr-4 align-top text-blue-600">
                        {isExpanded
                          ? "Hide"
                          : "Details"}
                      </td>
                    </tr>

                    {isExpanded && (
                      <tr className="bg-blue-50/50">
                        <td
                          colSpan={6}
                          className="px-4 py-3 text-sm text-gray-600"
                        >
                          <div className="space-y-2">
                            <p>
                              <span className="font-semibold text-gray-800">
                                Reasoning:
                              </span>{" "}
                              {
                                sentence.reasoning
                              }
                            </p>

                            <p>
                              <span className="font-semibold text-gray-800">
                                Confidence:
                              </span>{" "}
                              {(
                                sentence.confidence *
                                100
                              ).toFixed(0)}
                              %
                            </p>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              }
            )}
          </tbody>
        </table>

        {filteredSentences.length === 0 && (
          <div className="py-10 text-center text-sm text-gray-400">
            No sentences match the selected filters.
          </div>
        )}
      </div>
    </div>
  );
}