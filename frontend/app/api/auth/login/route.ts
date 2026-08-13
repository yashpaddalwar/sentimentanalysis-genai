import { NextResponse } from "next/server";
import { createSessionToken } from "@/lib/session";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const body = await request.json();

    const username = String(body?.username ?? "");
    const password = String(body?.password ?? "");

    const validUsername =
      process.env.APP_USERNAME ??
      process.env.NEXT_PUBLIC_APP_USERNAME;

    const validPassword =
      process.env.APP_PASSWORD ??
      process.env.NEXT_PUBLIC_APP_PASSWORD;

    if (!validUsername || !validPassword) {
      return NextResponse.json(
        {
          detail: "Application authentication is not configured.",
        },
        { status: 500 }
      );
    }

    if (
      username !== validUsername ||
      password !== validPassword
    ) {
      return NextResponse.json(
        {
          detail: "Invalid username or password.",
        },
        { status: 401 }
      );
    }

    const token = createSessionToken(username);

    return NextResponse.json({
      token,
    });
  } catch {
    return NextResponse.json(
      {
        detail: "Invalid authentication request.",
      },
      { status: 400 }
    );
  }
}