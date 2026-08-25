import { NextRequest, NextResponse } from "next/server";

const REGISTRY_API_URL =
  process.env.REGISTRY_API_URL || "http://dhg-registry-api:8000";

/** Streaming proxy for the registry logs-chat SSE endpoint (P5 T11).
 *
 * Dedicated route (not the generic /api/registry proxy) because SSE needs the
 * upstream ReadableStream passed through untouched — the generic proxy
 * buffers via arrayBuffer() and aborts at 15 s, which kills a 45 s-budget
 * stream. LOGS_CHAT_TOKEN is injected server-side; the browser never sees it. */
export async function POST(req: NextRequest) {
  const token = process.env.LOGS_CHAT_TOKEN;
  if (!token) {
    return NextResponse.json({ detail: "logs-chat not configured" }, { status: 503 });
  }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60_000); // > 45 s budget
  try {
    const upstream = await fetch(`${REGISTRY_API_URL}/api/logs/chat`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: `Bearer ${token}`,
      },
      body: await req.text(),
      signal: controller.signal,
    });
    // Headers are back — the abort timer's job (bounding connect/header time)
    // is done. The stream itself is bounded by the upstream 45 s budget.
    clearTimeout(timeout);
    if (!upstream.body) {
      return NextResponse.json({ detail: "empty upstream body" }, { status: 502 });
    }
    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers: {
        "content-type": upstream.headers.get("content-type") || "text/event-stream",
        "cache-control": "no-cache",
      },
    });
  } catch (err) {
    clearTimeout(timeout);
    console.error("[logs-chat] proxy failed", err);
    return NextResponse.json({ detail: "logs-chat upstream unreachable" }, { status: 502 });
  }
}
