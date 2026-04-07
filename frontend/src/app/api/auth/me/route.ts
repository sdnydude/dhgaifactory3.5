import { NextRequest, NextResponse } from "next/server";

const REGISTRY_API_URL =
  process.env.REGISTRY_API_URL || "http://dhg-registry-api:8000";

export async function GET(req: NextRequest) {
  const cfToken = req.cookies.get("CF_Authorization")?.value;
  const headers: Record<string, string> = {
    accept: "application/json",
  };
  if (cfToken) {
    headers["Cf-Access-Jwt-Assertion"] = cfToken;
  }

  try {
    const response = await fetch(`${REGISTRY_API_URL}/api/v1/security/users/me`, {
      headers,
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: "Not authenticated" },
        { status: response.status },
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      { error: "Auth service unavailable" },
      { status: 503 },
    );
  }
}
