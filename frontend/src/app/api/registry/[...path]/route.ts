import { NextRequest, NextResponse } from "next/server";

const REGISTRY_API_URL =
  process.env.REGISTRY_API_URL || "http://dhg-registry-api:8000";

async function proxyRequest(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  const targetPath = path.join("/");
  const url = new URL(targetPath, REGISTRY_API_URL + "/");

  req.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.set(key, value);
  });

  const headers: Record<string, string> = {
    accept: req.headers.get("accept") || "application/json",
  };

  const cfToken = req.cookies.get("CF_Authorization")?.value;
  if (cfToken) {
    headers["Cf-Access-Jwt-Assertion"] = cfToken;
  }

  const contentType = req.headers.get("content-type");
  if (contentType) {
    headers["content-type"] = contentType;
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15_000);

  const fetchOptions: RequestInit = {
    method: req.method,
    headers,
    signal: controller.signal,
  };

  if (req.method !== "GET" && req.method !== "HEAD") {
    fetchOptions.body = await req.text();
  }

  try {
    const response = await fetch(url.toString(), fetchOptions);
    const body = await response.arrayBuffer();

    const outHeaders: Record<string, string> = {
      "content-type": response.headers.get("content-type") || "application/octet-stream",
    };
    const disposition = response.headers.get("content-disposition");
    if (disposition) outHeaders["content-disposition"] = disposition;
    const cacheControl = response.headers.get("cache-control");
    if (cacheControl) outHeaders["cache-control"] = cacheControl;

    return new NextResponse(body, {
      status: response.status,
      headers: outHeaders,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "unknown";
    console.error(`[registry-proxy] ${req.method} /${targetPath} failed: ${message}`);
    return NextResponse.json(
      { error: "Registry API unavailable" },
      { status: 503 },
    );
  } finally {
    clearTimeout(timeout);
  }
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const DELETE = proxyRequest;
export const PATCH = proxyRequest;
