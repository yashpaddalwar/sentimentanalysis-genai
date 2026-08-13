import crypto from "crypto";

interface SessionPayload {
  sub: string;
  exp: number;
}

function getAuthSecret(): string {
  const secret = process.env.AUTH_SECRET;

  if (!secret || secret.length < 32) {
    throw new Error(
      "AUTH_SECRET must be configured and at least 32 characters long."
    );
  }

  return secret;
}

function base64UrlEncode(value: string | Buffer): string {
  return Buffer.from(value)
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

function base64UrlDecode(value: string): string {
  const padded = value
    .replace(/-/g, "+")
    .replace(/_/g, "/")
    .padEnd(Math.ceil(value.length / 4) * 4, "=");

  return Buffer.from(padded, "base64").toString("utf8");
}

export function createSessionToken(username: string): string {
  const payload: SessionPayload = {
    sub: username,
    exp: Math.floor(Date.now() / 1000) + 8 * 60 * 60,
  };

  const encodedPayload = base64UrlEncode(
    JSON.stringify(payload)
  );

  const signature = base64UrlEncode(
    crypto
      .createHmac("sha256", getAuthSecret())
      .update(encodedPayload)
      .digest()
  );

  return `${encodedPayload}.${signature}`;
}

export function verifySessionToken(
  token: string
): SessionPayload | null {
  try {
    const [encodedPayload, suppliedSignature] = token.split(".");

    if (!encodedPayload || !suppliedSignature) {
      return null;
    }

    const expectedSignature = base64UrlEncode(
      crypto
        .createHmac("sha256", getAuthSecret())
        .update(encodedPayload)
        .digest()
    );

    const expectedBuffer = Buffer.from(expectedSignature);
    const suppliedBuffer = Buffer.from(suppliedSignature);

    if (
      expectedBuffer.length !== suppliedBuffer.length ||
      !crypto.timingSafeEqual(
        expectedBuffer,
        suppliedBuffer
      )
    ) {
      return null;
    }

    const payload = JSON.parse(
      base64UrlDecode(encodedPayload)
    ) as SessionPayload;

    if (
      !payload.sub ||
      !payload.exp ||
      payload.exp <= Math.floor(Date.now() / 1000)
    ) {
      return null;
    }

    return payload;
  } catch {
    return null;
  }
}