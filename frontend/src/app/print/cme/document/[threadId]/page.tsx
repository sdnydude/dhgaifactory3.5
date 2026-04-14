import { notFound } from "next/navigation";

import { DocumentPrint } from "@/components/print/document-print";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ threadId: string }>;
  searchParams: Promise<{ t?: string }>;
}

async function fetchDocument(threadId: string, token: string) {
  const registry = process.env.REGISTRY_INTERNAL_URL ?? "http://dhg-registry-api:8000";
  const res = await fetch(
    `${registry}/api/cme/export/internal/document/${threadId}`,
    {
      headers: { "X-Print-Token": token },
      cache: "no-store",
    },
  );
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`registry fetch failed: ${res.status}`);
  return res.json() as Promise<{
    title: string;
    graph_label: string;
    review_round: number;
    document_text: string;
  }>;
}

export default async function Page({ params, searchParams }: Props) {
  const { threadId } = await params;
  const { t } = await searchParams;
  if (!t) notFound();
  const data = await fetchDocument(threadId, t);
  if (!data) notFound();
  return (
    <DocumentPrint
      title={data.title}
      graphLabel={data.graph_label}
      reviewRound={data.review_round}
      documentText={data.document_text}
      generatedAt={new Date().toISOString()}
    />
  );
}
