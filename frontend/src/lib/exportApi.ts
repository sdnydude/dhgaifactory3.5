const BASE = "/api/registry/api/cme/export";

function sanitizeFilename(name: string): string {
  const cleaned = name
    .replace(/[\/\\?%*:|"<>\x00-\x1f]/g, "_")
    .replace(/^\.+/, "_")
    .trim();
  return (cleaned || "document").slice(0, 200);
}

export async function downloadDocument(threadId: string, suggestedName: string): Promise<void> {
  const res = await fetch(`${BASE}/document/${encodeURIComponent(threadId)}`, {
    method: "GET",
    credentials: "include",
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`download failed: ${res.status} ${res.statusText}${body ? ` — ${body.slice(0, 200)}` : ""}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  try {
    a.href = url;
    a.download = `${sanitizeFilename(suggestedName)}.pdf`;
    document.body.appendChild(a);
    a.click();
  } finally {
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }
}
