import { NextRequest, NextResponse } from "next/server";

const PROMETHEUS_URL =
  process.env.PROMETHEUS_URL || "http://dhg-prometheus:9090";

async function proxyRequest(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  const targetPath = path.join("/");
  const url = new URL(targetPath, PROMETHEUS_URL + "/");

  req.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.set(key, value);
  });

  try {
    const response = await fetch(url.toString(), {
      method: req.method,
      headers: { accept: req.headers.get("accept") || "application/json" },
      cache: "no-store",
    });

    const contentType = response.headers.get("content-type") || "";
    const body = await response.text();

    return new NextResponse(body, {
      status: response.status,
      headers: { "content-type": contentType },
    });
  } catch {
    return NextResponse.json(
      { error: "Prometheus unavailable" },
      { status: 503 },
    );
  }
}

export const GET = proxyRequest;
