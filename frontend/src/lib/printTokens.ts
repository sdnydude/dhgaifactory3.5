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

function b64urlToBytes(input: string): Uint8Array {
  const pad = "=".repeat((4 - (input.length % 4)) % 4);
  const b64 = (input + pad).replace(/-/g, "+").replace(/_/g, "/");
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function bytesToB64url(buf: ArrayBuffer): string {
  const u8 = new Uint8Array(buf);
  let bin = "";
  for (let i = 0; i < u8.length; i++) bin += String.fromCharCode(u8[i]);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function constantTimeEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a[i] ^ b[i];
  return diff === 0;
}

export async function verifyPrintToken(
  token: string,
  secret: string,
): Promise<PrintTokenPayload> {
  const dot = token.lastIndexOf(".");
  if (dot < 0) throw new PrintTokenInvalid("malformed token");
  const body = token.slice(0, dot);
  const sig = token.slice(dot + 1);

  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const macBuf = await crypto.subtle.sign("HMAC", key, enc.encode(body));
  const expected = bytesToB64url(macBuf);

  let sigBytes: Uint8Array;
  let expBytes: Uint8Array;
  try {
    sigBytes = b64urlToBytes(sig);
    expBytes = b64urlToBytes(expected);
  } catch {
    throw new PrintTokenInvalid("bad signature encoding");
  }
  if (!constantTimeEqual(expBytes, sigBytes)) {
    throw new PrintTokenInvalid("bad signature");
  }

  let payload: PrintTokenPayload;
  try {
    const json = new TextDecoder().decode(b64urlToBytes(body));
    payload = JSON.parse(json);
  } catch {
    throw new PrintTokenInvalid("bad payload");
  }
  if (payload.expires_at <= Math.floor(Date.now() / 1000)) {
    throw new PrintTokenExpired("token expired");
  }
  return payload;
}
