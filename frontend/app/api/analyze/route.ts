import { NextResponse } from "next/server";
import { verifySessionToken } from "@/lib/session";

export const runtime = "nodejs";

export async function POST(request: Request) {
  const authorization = request.headers.get("authorization");

  if (!authorization?.startsWith("Bearer ")) {
    return NextResponse.json(
      { detail: "Authentication required." },
      { status: 401 }
    );
  }

  const sessionToken = authorization.slice("Bearer ".length).trim();

  if (!verifySessionToken(sessionToken)) {
    return NextResponse.json(
      { detail: "Invalid or expired session." },
      { status: 401 }
    );
  }

  const backendUrl =
    process.env.BACKEND_URL ??
    process.env.NEXT_PUBLIC_API_URL;

  const backendApiKey =
    process.env.BACKEND_API_KEY ??
    process.env.NEXT_PUBLIC_API_KEY ??
    "";

  if (!backendUrl) {
    return NextResponse.json(
      { detail: "Backend URL is not configured." },
      { status: 500 }
    );
  }

  try {
    const incomingFormData = await request.formData();

    const uploadedFile = incomingFormData.get("file");

    if (!(uploadedFile instanceof File)) {
      return NextResponse.json(
        { detail: "A .txt transcript file is required." },
        { status: 400 }
      );
    }

    const formData = new FormData();

    formData.append(
      "file",
      uploadedFile,
      uploadedFile.name
    );

    const backendResponse = await fetch(
      `${backendUrl.replace(/\/+$/, "")}/analyze`,
      {
        method: "POST",
        headers: {
          ...(backendApiKey
            ? { "X-API-Key": backendApiKey }
            : {}),
        },
        body: formData,
        cache: "no-store",
      }
    );

    const responseText = await backendResponse.text();

    return new NextResponse(responseText, {
      status: backendResponse.status,
      headers: {
        "Content-Type":
          backendResponse.headers.get("content-type") ??
          "application/json",
      },
    });
  } catch {
    return NextResponse.json(
      {
        detail:
          "Unable to reach the analysis backend.",
      },
      { status: 502 }
    );
  }
}