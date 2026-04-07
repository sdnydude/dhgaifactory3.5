export interface CfAccessClaims {
  email: string;
  sub: string;
  iat: number;
  exp: number;
  iss: string;
  custom?: Record<string, unknown>;
}

export function decodeCfJwt(token: string): CfAccessClaims | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1]));
    if (payload.exp && payload.exp * 1000 < Date.now()) return null;
    return payload as CfAccessClaims;
  } catch {
    return null;
  }
}

export function getCfJwtFromCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie
    .split("; ")
    .find((c) => c.startsWith("CF_Authorization="));
  return match ? match.split("=")[1] : null;
}
