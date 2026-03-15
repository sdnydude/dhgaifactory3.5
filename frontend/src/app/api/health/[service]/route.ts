import { NextRequest, NextResponse } from "next/server";

const SERVICE_URLS: Record<string, string> = {
  prometheus: process.env.PROMETHEUS_URL || "http://localhost:9090",
  grafana: process.env.GRAFANA_URL || "http://localhost:3001",
  ollama: process.env.OLLAMA_URL || "http://localhost:11434",
};

const HEALTH_PATHS: Record<string, string> = {
  prometheus: "/-/healthy",
  grafana: "/api/health",
  ollama: "/",
};

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ service: string }> },
) {
  const { service } = await params;
  const baseUrl = SERVICE_URLS[service];
  const healthPath = HEALTH_PATHS[service];

  if (!baseUrl || !healthPath) {
    return NextResponse.json(
      { error: `Unknown service: ${service}` },
      { status: 404 },
    );
  }

  try {
    const response = await fetch(`${baseUrl}${healthPath}`);
    return NextResponse.json(
      { status: response.ok ? "healthy" : "unhealthy" },
      { status: response.ok ? 200 : 502 },
    );
  } catch (e) {
    const message = e instanceof Error ? e.message : "Unknown error";
    console.error(`Health check failed for ${service}:`, message);
    return NextResponse.json(
      { error: `${service} unreachable`, detail: message },
      { status: 503 },
    );
  }
}
