import { NextRequest, NextResponse } from "next/server";

const SESSION_LOGGER_URL =
  process.env.SESSION_LOGGER_URL || "http://dhg-session-logger:8009";

async function proxyRequest(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  const targetPath = path.join("/");
  const url = new URL(targetPath, SESSION_LOGGER_URL + "/");

  req.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.set(key, value);
  });

  try {
    const response = await fetch(url.toString(), {
      method: req.method,
      headers: { accept: req.headers.get("accept") || "application/json" },
    });

    const contentType = response.headers.get("content-type") || "";
    const body = await response.text();

    return new NextResponse(body, {
      status: response.status,
      headers: { "content-type": contentType },
    });
  } catch {
    return NextResponse.json(
      { error: "Session logger unavailable" },
      { status: 503 },
    );
  }
}

export const GET = proxyRequest;
