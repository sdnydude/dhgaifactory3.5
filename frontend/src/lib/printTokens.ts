import { createHmac, timingSafeEqual } from "node:crypto";

export class PrintTokenInvalid extends Error {}
export class PrintTokenExpired extends Error {}

export type Subject =
  | "cme_document"
  | "cme_project_intake"
  | "cme_quality"
  | "cme_review_history";

export interface PrintTokenPayload {
  subject: Subject;
  resource_id: string;
  expires_at: number;
}

function b64urlDecode(input: string): Buffer {
  const pad = "=".repeat((4 - (input.length % 4)) % 4);
  return Buffer.from(input + pad, "base64url");
}

function b64urlEncode(buf: Buffer): string {
  return buf.toString("base64url");
}

export function verifyPrintToken(token: string, secret: string): PrintTokenPayload {
  const dot = token.lastIndexOf(".");
  if (dot < 0) throw new PrintTokenInvalid("malformed token");
  const body = token.slice(0, dot);
  const sig = token.slice(dot + 1);

  const expected = b64urlEncode(createHmac("sha256", secret).update(body).digest());
  const a = Buffer.from(expected);
  const b = Buffer.from(sig);
  if (a.length !== b.length || !timingSafeEqual(a, b)) {
    throw new PrintTokenInvalid("bad signature");
  }

  let payload: PrintTokenPayload;
  try {
    payload = JSON.parse(b64urlDecode(body).toString("utf-8"));
  } catch {
    throw new PrintTokenInvalid("bad payload");
  }
  if (payload.expires_at <= Math.floor(Date.now() / 1000)) {
    throw new PrintTokenExpired("token expired");
  }
  return payload;
}
