import { NextRequest, NextResponse } from "next/server";

// Route access by role — mirrors lib/permissions.ts
// Duplicated here because middleware runs in Edge Runtime and can't import from src/lib
const ROUTE_ROLES: Record<string, string[]> = {
  "/projects": ["admin", "operations", "finance", "editor", "viewer"],
  "/inbox": ["admin", "operations", "editor", "viewer"],
  "/chat": ["admin", "operations", "editor"],
  "/search": ["admin", "operations", "editor"],
  "/agents": ["admin", "operations"],
  "/dashboards": ["admin", "operations", "finance"],
  "/monitoring": ["admin", "operations"],
  "/studio": ["admin", "operations"],
  "/admin": ["admin"],
};

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    return JSON.parse(atob(parts[1]));
  } catch {
    return null;
  }
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip API routes, static files, and the root redirect
  if (
    pathname.startsWith("/api/") ||
    pathname.startsWith("/_next/") ||
    pathname === "/" ||
    pathname.startsWith("/favicon")
  ) {
    return NextResponse.next();
  }

  // In dev mode, allow everything
  if (process.env.NEXT_PUBLIC_SECURITY_DEV_MODE === "true") {
    return NextResponse.next();
  }

  // Find matching route
  const matchedRoute = Object.keys(ROUTE_ROLES).find((route) =>
    pathname.startsWith(route)
  );
  if (!matchedRoute) return NextResponse.next();

  // Get JWT from cookie
  const cfToken = request.cookies.get("CF_Authorization")?.value;
  if (!cfToken) {
    // No auth — redirect to projects (Cloudflare Access handles actual login)
    return NextResponse.redirect(new URL("/projects", request.url));
  }

  // Decode JWT to get email, then check roles via a header passed to the page
  // Note: Full role resolution happens client-side via useSession.
  // Middleware provides a first-pass guard; the definitive check is the API.
  const claims = decodeJwtPayload(cfToken);
  if (!claims) {
    return NextResponse.redirect(new URL("/projects", request.url));
  }

  // Pass the email through to the page via a header for SSR use
  const response = NextResponse.next();
  response.headers.set("x-user-email", (claims.email as string) || "");
  return response;
}

export const config = {
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};
