"use client";

import { useCallback, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LogStream, type LogEntry } from "@/components/agents/log-stream";
import { cn } from "@/lib/utils";

/** /logs — ask a question about container logs (P5 T11).
 *
 * Design per the P5 design review: monitoring-page header pattern (status dot
 * + updated-ago), plain question bar (no chat bubbles), Badge-based citation
 * chips, LogStream terminal panel on the shared mc-* tokens, honest degraded
 * state (partial answer retained, banner appended). Desktop ops console —
 * mobile responsiveness is a stated non-goal beyond not breaking. */

type Phase = "idle" | "streaming" | "complete" | "degraded" | "error";

interface QuerySpec {
  desc: string;
  logql: string;
  lines: number;
}

interface Citations {
  container: string | null;
  queries: QuerySpec[];
  sample?: string[];
}

function parseSse(buffer: string): { events: { event: string; data: string }[]; rest: string } {
  const events: { event: string; data: string }[] = [];
  const parts = buffer.split("\n\n");
  const rest = parts.pop() ?? "";
  for (const part of parts) {
    let event = "message";
    const dataLines: string[] = [];
    for (const line of part.split("\n")) {
      if (line.startsWith("event: ")) event = line.slice(7);
      else if (line.startsWith("data: ")) dataLines.push(line.slice(6));
    }
    if (dataLines.length) events.push({ event, data: dataLines.join("\n") });
  }
  return { events, rest };
}

export default function LogsPage() {
  const [question, setQuestion] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citations | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [elapsedMs, setElapsedMs] = useState<number | null>(null);
  const busyRef = useRef(false);

  const ask = useCallback(async () => {
    const q = question.trim();
    if (q.length < 3 || busyRef.current) return;
    busyRef.current = true;
    setPhase("streaming"); setAnswer(""); setCitations(null); setNotice(null); setElapsedMs(null);
    try {
      const res = await fetch("/api/logs-chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      if (!res.ok || !res.body) {
        const body = await res.json().catch(() => null);
        setPhase("error"); setNotice(body?.detail ?? `logs-chat unavailable (${res.status})`);
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let terminal: Phase = "complete";
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const { events, rest } = parseSse(buf);
        buf = rest;
        for (const { event, data } of events) {
          let payload;
          try {
            payload = JSON.parse(data);
          } catch (err) {
            console.error("[logs-chat] bad SSE payload", event, data, err);
            continue; // skip the bad event, keep the in-flight answer
          }
          if (event === "citations") setCitations(payload);
          else if (event === "delta") setAnswer((a) => a + payload.text);
          else if (event === "degraded") { terminal = "degraded"; setNotice(payload.message); setElapsedMs(payload.elapsed_ms); }
          else if (event === "error") { terminal = "error"; setNotice(payload.message); }
          else if (event === "done") setElapsedMs(payload.elapsed_ms);
        }
      }
      setPhase(terminal);
    } catch {
      setPhase("error");
      setNotice("Connection lost — the answer above may be incomplete.");
    } finally {
      busyRef.current = false;
    }
  }, [question]);

  const STATUS_COLORS: Record<Phase, string> = {
    idle: "bg-muted-foreground",
    streaming: "bg-green-500",
    complete: "bg-green-500",
    degraded: "bg-yellow-500",
    error: "bg-destructive",
  };
  const statusColor = STATUS_COLORS[phase];

  const logEntries: LogEntry[] = (citations?.sample ?? []).map((line, i) => ({
    id: String(i),
    timestamp: "",
    source: line.startsWith("[") ? line.slice(1, line.indexOf("]")) : "log",
    message: line.startsWith("[") ? line.slice(line.indexOf("]") + 2) : line,
    level: /error|fatal|panic/i.test(line) ? "error" : /warn/i.test(line) ? "warn" : "info",
  }));

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header — monitoring-page pattern */}
      <div className="flex items-center justify-between border-b px-6 py-4">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            {phase === "streaming" && (
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
            )}
            <span className={cn("relative inline-flex h-2.5 w-2.5 rounded-full", statusColor)} />
          </span>
          <h1 className="text-lg font-semibold">Logs</h1>
        </div>
        <span className="text-xs text-muted-foreground">
          {phase === "streaming" && "Streaming..."}
          {elapsedMs != null && phase !== "streaming" && `Answered in ${(elapsedMs / 1000).toFixed(1)}s`}
          {phase === "idle" && "Ask a question about container logs"}
        </span>
      </div>

      {/* Question bar — single primary action, no chat chrome */}
      <div className="flex items-center gap-3 border-b px-6 py-3">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") void ask(); }}
          placeholder="What errors did portage-api log in the last hour?"
          className="h-9 flex-1 rounded-md border bg-transparent px-3 text-sm outline-none focus:ring-1 focus:ring-ring"
          maxLength={500}
        />
        <Button size="sm" onClick={() => void ask()} disabled={phase === "streaming" || question.trim().length < 3}>
          Ask
        </Button>
      </div>

      <div className="flex-1 overflow-auto px-6 py-4">
        {/* Citations — Badge chips, not cards */}
        {citations && (
          <div className="mb-3 flex flex-wrap items-center gap-2">
            {citations.container && <Badge variant="secondary">container: {citations.container}</Badge>}
            {citations.queries.map((q) => (
              <Badge
                key={q.logql}
                variant="outline"
                className="font-mono text-[11px]"
                title={q.logql}
              >
                {q.desc} · {q.lines}
              </Badge>
            ))}
          </div>
        )}

        {/* Degraded / error banner — monitoring pattern; partial answer stays */}
        {notice && (
          <div className="mb-3 flex items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-2.5">
            <span className="text-sm text-destructive">{notice}</span>
          </div>
        )}

        {/* Streamed answer — plain prose */}
        {answer && (
          <p className="mb-4 whitespace-pre-wrap text-sm leading-relaxed">{answer}</p>
        )}
        {phase === "idle" && (
          <p className="text-sm text-muted-foreground">
            Answers are grounded in the log lines retrieved below — nothing is invented.
          </p>
        )}

        {/* Log sample — terminal panel on shared mc-* tokens */}
        {logEntries.length > 0 && (
          <div className="mc-root h-72 overflow-hidden rounded-md border">
            <LogStream logs={logEntries} footer={`${logEntries.length} sampled lines`} />
          </div>
        )}
      </div>
    </div>
  );
}
