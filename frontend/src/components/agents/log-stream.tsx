"use client";

import { useEffect, useRef } from "react";

interface LogEntry {
  timestamp: string;
  source: string;
  message: string;
  level: "info" | "warn" | "error" | "debug";
}

const LEVEL_COLORS: Record<string, string> = {
  info: "text-green-400",
  warn: "text-yellow-400",
  error: "text-red-400",
  debug: "text-blue-400",
};

interface LogStreamProps {
  logs: LogEntry[];
}

export function LogStream({ logs }: LogStreamProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length]);

  return (
    <div className="bg-[#0d1117] text-[#c9d1d9] rounded-md p-3 font-mono text-[11px] leading-relaxed overflow-auto max-h-[400px]">
      {logs.length === 0 ? (
        <p className="text-gray-500">Waiting for log events...</p>
      ) : (
        logs.map((log, i) => (
          <div key={i} className="flex gap-2">
            <span className="text-gray-500 shrink-0">{log.timestamp}</span>
            <span className={`shrink-0 w-12 ${LEVEL_COLORS[log.level] ?? "text-gray-400"}`}>
              [{log.level.toUpperCase()}]
            </span>
            <span className="text-cyan-400 shrink-0">{log.source}</span>
            <span>{log.message}</span>
          </div>
        ))
      )}
      <div ref={bottomRef} />
    </div>
  );
}

export type { LogEntry };
