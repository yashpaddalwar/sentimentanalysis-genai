"use client";

import { useCallback, useRef, useState } from "react";

interface UploadZoneProps {
  onAnalyze: (file: File) => void;
  loading: boolean;
}

export default function UploadZone({ onAnalyze, loading }: UploadZoneProps) {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = (f: File) => {
    if (!f.name.toLowerCase().endsWith(".txt")) {
      alert("Please upload a .txt file.");
      return;
    }
    setFile(f);
  };

  const onDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragActive(false);
    const f = e.dataTransfer.files?.[0];
    if (f) handleFile(f);
  }, []);

  return (
    <div className="rounded-2xl bg-white p-6 shadow-md">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-10 text-center transition ${
          dragActive
            ? "border-blue-500 bg-blue-50"
            : "border-gray-300 bg-gray-50 hover:bg-gray-100"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".txt"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
          }}
        />
        <p className="text-sm font-medium text-gray-700">
          {file
            ? `Selected: ${file.name}`
            : "Drag & drop a .txt transcript here, or click to browse"}
        </p>
        <p className="mt-1 text-xs text-gray-400">Only .txt files are supported</p>
      </div>

      <button
        disabled={!file || loading}
        onClick={() => file && onAnalyze(file)}
        className="mt-4 w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300"
      >
        {loading ? "Analyzing..." : "Analyze Transcript"}
      </button>
    </div>
  );
}