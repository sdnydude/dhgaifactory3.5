import { describe, expect, it } from "vitest";
import { createHmac } from "node:crypto";

import { PrintTokenInvalid, PrintTokenExpired, verifyPrintToken } from "./printTokens";

const SECRET = "a".repeat(64);

function sign(payload: object): string {
  const body = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const sig = createHmac("sha256", SECRET).update(body).digest().toString("base64url");
  return `${body}.${sig}`;
}

describe("verifyPrintToken", () => {
  it("accepts a valid token", () => {
    const token = sign({
      subject: "cme_document",
      resource_id: "thread-abc",
      expires_at: Math.floor(Date.now() / 1000) + 60,
    });
    const payload = verifyPrintToken(token, SECRET);
    expect(payload.resource_id).toBe("thread-abc");
  });

  it("rejects tampered signature", () => {
    const token = sign({
      subject: "cme_document",
      resource_id: "thread-abc",
      expires_at: Math.floor(Date.now() / 1000) + 60,
    });
    const [body] = token.split(".");
    expect(() => verifyPrintToken(`${body}.${"A".repeat(43)}`, SECRET)).toThrow(
      PrintTokenInvalid,
    );
  });

  it("rejects expired token", () => {
    const token = sign({
      subject: "cme_document",
      resource_id: "thread-abc",
      expires_at: Math.floor(Date.now() / 1000) - 1,
    });
    expect(() => verifyPrintToken(token, SECRET)).toThrow(PrintTokenExpired);
  });
});
