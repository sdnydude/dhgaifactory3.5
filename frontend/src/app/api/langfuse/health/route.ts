import { NextResponse } from "next/server";

const LANGFUSE_URL = process.env.LANGFUSE_URL || "http://10.0.0.179:3000";

/**
 * Server-side liveness probe for Langfuse. Called from the sidebar status
 * dot; the browser never talks to Langfuse directly, so no key is involved
 * and a Langfuse outage stays a 200 with status "down" rather than a
 * console error on every page.
 */
export async function GET() {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5_000);

  try {
    const res = await fetch(`${LANGFUSE_URL}/api/public/health`, {
      signal: controller.signal,
      cache: "no-store",
    });
    return NextResponse.json({ status: res.ok ? "ok" : "down" });
  } catch {
    return NextResponse.json({ status: "down" });
  } finally {
    clearTimeout(timeout);
  }
}
