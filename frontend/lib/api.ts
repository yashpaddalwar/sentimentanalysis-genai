import { AnalysisResponse } from "@/types";
import { getSessionToken } from "@/lib/auth";

export async function analyzeTranscript(
  file: File
): Promise<AnalysisResponse> {
  const token = getSessionToken();

  if (!token) {
    throw new Error(
      "Your session has expired. Please log in again."
    );
  }

  const formData = new FormData();

  formData.append("file", file);

  const response = await fetch(
    "/api/analyze",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
      cache: "no-store",
    }
  );

  if (!response.ok) {
    let detail =
      "Failed to analyze transcript.";

    try {
      const errorBody = await response.json();

      if (typeof errorBody?.detail === "string") {
        detail = errorBody.detail;
      }
    } catch {
      // Ignore malformed error payloads.
    }

    if (response.status === 401) {
      throw new Error(
        "Your session has expired. Please log in again."
      );
    }

    throw new Error(detail);
  }

  return response.json() as Promise<AnalysisResponse>;
}