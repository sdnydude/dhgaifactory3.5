import { NextRequest, NextResponse } from "next/server";

const LANGGRAPH_CLOUD_URL =
  process.env.LANGGRAPH_API_URL ||
  "https://dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app";

const LANGCHAIN_API_KEY = process.env.LANGCHAIN_API_KEY || "";

async function proxyRequest(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  const targetPath = path.join("/");
  const url = new URL(targetPath, LANGGRAPH_CLOUD_URL + "/");

  req.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.set(key, value);
  });

  const headers: Record<string, string> = {
    "x-api-key": LANGCHAIN_API_KEY,
  };

  const contentType = req.headers.get("content-type");
  if (contentType) {
    headers["content-type"] = contentType;
  }

  const accept = req.headers.get("accept");
  if (accept) {
    headers["accept"] = accept;
  }

  const fetchOptions: RequestInit = {
    method: req.method,
    headers,
  };

  if (req.method !== "GET" && req.method !== "HEAD") {
    fetchOptions.body = await req.text();
  }

  const response = await fetch(url.toString(), fetchOptions);

  const responseContentType = response.headers.get("content-type") || "";

  if (responseContentType.includes("text/event-stream")) {
    return new Response(response.body, {
      status: response.status,
      headers: {
        "content-type": "text/event-stream",
        "cache-control": "no-cache",
        connection: "keep-alive",
      },
    });
  }

  const body = await response.text();
  return new NextResponse(body, {
    status: response.status,
    headers: {
      "content-type": responseContentType,
    },
  });
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const DELETE = proxyRequest;
export const PATCH = proxyRequest;
