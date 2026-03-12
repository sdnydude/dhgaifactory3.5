"use client";

import { useState, useCallback } from "react";
import { Search, FileText, BookOpen, FormInput, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Toggle } from "@/components/ui/toggle";
import { hybridSearch } from "@/lib/registryApi";
import type { SearchResultItem } from "@/types/cme";
import Link from "next/link";

const SOURCE_FILTERS = [
  { key: "cme_documents", label: "Documents", icon: FileText },
  { key: "cme_intake_fields", label: "Intake Fields", icon: FormInput },
  { key: "cme_source_references", label: "References", icon: BookOpen },
] as const;

const SOURCE_LABELS: Record<string, string> = {
  cme_documents: "Document",
  cme_intake_fields: "Intake Field",
  cme_source_references: "Reference",
};

function ResultCard({ result }: { result: SearchResultItem }) {
  const sourceLabel = SOURCE_LABELS[result.source_table] ?? result.source_table;

  return (
    <Card className="hover:border-primary/30 transition-colors">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <CardTitle className="text-sm leading-snug line-clamp-2">
              {result.title}
            </CardTitle>
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            <Badge variant="outline" className="text-[10px]">
              {sourceLabel}
            </Badge>
            <Badge variant="secondary" className="text-[10px] tabular-nums">
              {result.score.toFixed(3)}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {result.snippet && (
          <p className="text-xs text-muted-foreground line-clamp-3 mb-2">
            {result.snippet}
          </p>
        )}
        <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
          <Link
            href={`/projects/${result.project_id}`}
            className="text-primary hover:underline"
          >
            View project
          </Link>
          {result.metadata.document_type ? (
            <span>{String(result.metadata.document_type)}</span>
          ) : null}
          {result.metadata.word_count ? (
            <span>{Number(result.metadata.word_count).toLocaleString()} words</span>
          ) : null}
          {result.metadata.journal ? (
            <span className="truncate max-w-[200px]">{String(result.metadata.journal)}</span>
          ) : null}
          {result.metadata.ref_id ? (
            <span>PMID: {String(result.metadata.ref_id)}</span>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [activeSources, setActiveSources] = useState<Set<string>>(
    new Set(["cme_documents", "cme_intake_fields", "cme_source_references"]),
  );

  const toggleSource = (key: string) => {
    setActiveSources((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        if (next.size > 1) next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const doSearch = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const resp = await hybridSearch({
        query: query.trim(),
        source_tables: Array.from(activeSources),
        limit: 30,
      });
      setResults(resp.results);
      setTotal(resp.total);
    } catch (err) {
      console.error("Search failed:", err);
      setResults([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [query, activeSources]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") doSearch();
  };

  return (
    <div className="flex-1 overflow-auto">
      <div className="max-w-3xl mx-auto px-6 py-8">
        <h1 className="text-lg font-semibold mb-1">Search CME Knowledge Base</h1>
        <p className="text-sm text-muted-foreground mb-6">
          Hybrid full-text + vector search across documents, intake fields, and references.
        </p>

        {/* Search bar */}
        <div className="flex gap-2 mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Search documents, references, intake fields..."
              className="pl-9"
            />
          </div>
          <Button onClick={doSearch} disabled={loading || !query.trim()}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Search"}
          </Button>
        </div>

        {/* Source filters */}
        <div className="flex items-center gap-2 mb-6">
          <span className="text-xs text-muted-foreground">Sources:</span>
          {SOURCE_FILTERS.map(({ key, label, icon: Icon }) => (
            <Toggle
              key={key}
              size="sm"
              pressed={activeSources.has(key)}
              onPressedChange={() => toggleSource(key)}
              className="h-7 text-xs gap-1.5 data-[state=on]:bg-primary/10"
            >
              <Icon className="h-3 w-3" />
              {label}
            </Toggle>
          ))}
        </div>

        {/* Results */}
        {loading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}

        {!loading && searched && results.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Search className="h-10 w-10 text-muted-foreground/50 mb-3" />
            <p className="text-sm text-muted-foreground">No results found</p>
            <p className="text-xs text-muted-foreground">
              Try different keywords or enable more source filters.
            </p>
          </div>
        )}

        {!loading && results.length > 0 && (
          <>
            <p className="text-xs text-muted-foreground mb-3">
              {total} result{total !== 1 ? "s" : ""}
            </p>
            <div className="space-y-3">
              {results.map((r) => (
                <ResultCard key={`${r.source_table}-${r.id}`} result={r} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
