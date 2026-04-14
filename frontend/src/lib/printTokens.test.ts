import { describe, expect, it } from "vitest";

import { PrintTokenInvalid, PrintTokenExpired, verifyPrintToken } from "./printTokens";

const SECRET = "a".repeat(64);

function bytesToB64url(buf: ArrayBuffer): string {
  const u8 = new Uint8Array(buf);
  let bin = "";
  for (let i = 0; i < u8.length; i++) bin += String.fromCharCode(u8[i]);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function sign(payload: object): Promise<string> {
  const enc = new TextEncoder();
  const body = bytesToB64url(enc.encode(JSON.stringify(payload)).buffer);
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(SECRET),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const mac = await crypto.subtle.sign("HMAC", key, enc.encode(body));
  const sig = bytesToB64url(mac);
  return `${body}.${sig}`;
}

describe("verifyPrintToken", () => {
  it("accepts a valid token", async () => {
    const token = await sign({
      subject: "cme_document",
      resource_id: "thread-abc",
      expires_at: Math.floor(Date.now() / 1000) + 60,
    });
    const payload = await verifyPrintToken(token, SECRET);
    expect(payload.resource_id).toBe("thread-abc");
  });

  it("rejects tampered signature", async () => {
    const token = await sign({
      subject: "cme_document",
      resource_id: "thread-abc",
      expires_at: Math.floor(Date.now() / 1000) + 60,
    });
    const [body] = token.split(".");
    await expect(verifyPrintToken(`${body}.${"A".repeat(43)}`, SECRET)).rejects.toThrow(
      PrintTokenInvalid,
    );
  });

  it("rejects expired token", async () => {
    const token = await sign({
      subject: "cme_document",
      resource_id: "thread-abc",
      expires_at: Math.floor(Date.now() / 1000) - 1,
    });
    await expect(verifyPrintToken(token, SECRET)).rejects.toThrow(PrintTokenExpired);
  });
});
