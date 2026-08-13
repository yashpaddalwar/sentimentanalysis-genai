"use client";

import {
  useRef,
  useState,
} from "react";

interface UploadZoneProps {
  onAnalyze: (file: File) => void;
  loading: boolean;
}

const MAX_FILE_SIZE = 2 * 1024 * 1024;

export default function UploadZone({
  onAnalyze,
  loading,
}: UploadZoneProps) {
  const [file, setFile] =
    useState<File | null>(null);

  const [dragActive, setDragActive] =
    useState(false);

  const [error, setError] =
    useState("");

  const inputRef =
    useRef<HTMLInputElement>(null);

  function handleFile(candidate: File) {
    setError("");

    if (
      !candidate.name
        .toLowerCase()
        .endsWith(".txt")
    ) {
      setError(
        "Please upload a .txt transcript."
      );
      return;
    }

    if (candidate.size > MAX_FILE_SIZE) {
      setError(
        "Transcript must be 2 MB or smaller."
      );
      return;
    }

    setFile(candidate);
  }

  function handleDrop(
    event: React.DragEvent<HTMLDivElement>
  ) {
    event.preventDefault();
    setDragActive(false);

    const droppedFile =
      event.dataTransfer.files?.[0];

    if (droppedFile) {
      handleFile(droppedFile);
    }
  }

  return (
    <div className="rounded-2xl bg-white p-6 shadow-md">
      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() =>
          setDragActive(false)
        }
        onDrop={handleDrop}
        onClick={() =>
          inputRef.current?.click()
        }
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-10 text-center transition ${
          dragActive
            ? "border-blue-500 bg-blue-50"
            : "border-gray-300 bg-gray-50 hover:bg-gray-100"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".txt,text/plain"
          className="hidden"
          onChange={(event) => {
            const selectedFile =
              event.target.files?.[0];

            if (selectedFile) {
              handleFile(selectedFile);
            }
          }}
        />

        <div className="mb-3 text-3xl">
          📄
        </div>

        <p className="text-sm font-medium text-gray-700">
          {file
            ? file.name
            : "Drag & drop a .txt transcript here, or click to browse"}
        </p>

        <p className="mt-1 text-xs text-gray-400">
          UTF-8 plain text • Maximum 2 MB
        </p>
      </div>

      {error && (
        <p
          role="alert"
          className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600"
        >
          {error}
        </p>
      )}

      <button
        disabled={!file || loading}
        onClick={(event) => {
          event.stopPropagation();

          if (file) {
            onAnalyze(file);
          }
        }}
        className="mt-4 w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300"
      >
        {loading
          ? "Analyzing with AI..."
          : "Analyze Transcript"}
      </button>
    </div>
  );
}