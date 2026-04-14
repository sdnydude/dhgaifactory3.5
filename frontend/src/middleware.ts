import { NextRequest, NextResponse } from "next/server";
import { verifyPrintToken, PrintTokenInvalid, PrintTokenExpired } from "@/lib/printTokens";

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

const PRINT_SUBJECT_BY_PREFIX: Array<{ prefix: string; subject: string }> = [
  { prefix: "/print/cme/document/", subject: "cme_document" },
  { prefix: "/print/cme/project/", subject: "cme_project_intake" },
  { prefix: "/print/cme/quality/", subject: "cme_quality" },
  { prefix: "/print/cme/review-history/", subject: "cme_review_history" },
];

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    return JSON.parse(atob(parts[1]));
  } catch {
    return null;
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname.startsWith("/print/")) {
    const secret = process.env.EXPORT_SIGNING_SECRET;
    if (!secret) {
      return new NextResponse("print disabled", { status: 503 });
    }
    const token = request.nextUrl.searchParams.get("t");
    if (!token) {
      return new NextResponse("missing token", { status: 401 });
    }
    try {
      const payload = await verifyPrintToken(token, secret);
      const match = PRINT_SUBJECT_BY_PREFIX.find((m) => pathname.startsWith(m.prefix));
      if (!match || match.subject !== payload.subject) {
        return new NextResponse("subject mismatch", { status: 403 });
      }
      const tail = pathname.slice(match.prefix.length).split("/")[0];
      if (tail !== payload.resource_id) {
        return new NextResponse("resource mismatch", { status: 403 });
      }
      return NextResponse.next();
    } catch (err) {
      if (err instanceof PrintTokenExpired) {
        return new NextResponse("expired", { status: 401 });
      }
      if (err instanceof PrintTokenInvalid) {
        return new NextResponse("invalid", { status: 401 });
      }
      throw err;
    }
  }

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
