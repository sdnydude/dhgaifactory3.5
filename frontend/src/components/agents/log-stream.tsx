"use client";

import { useEffect, useRef, useState, useCallback } from "react";

interface LogEntry {
  id: string;
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
  footer?: string;
}

export function LogStream({ logs, footer }: LogStreamProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [scrollLocked, setScrollLocked] = useState(true);

  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    setScrollLocked(atBottom);
  }, []);

  useEffect(() => {
    if (scrollLocked) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs.length, scrollLocked]);

  return (
    <div className="relative h-full flex flex-col">
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="bg-[#0d1117] text-[#c9d1d9] rounded-md p-3 font-mono text-[11px] leading-relaxed overflow-auto flex-1"
      >
        {logs.length === 0 ? (
          <p className="text-gray-500">Waiting for stream events...</p>
        ) : (
          logs.map((log) => (
            <div key={log.id} className="flex gap-2">
              <span className="text-gray-500 shrink-0">{log.timestamp}</span>
              <span
                className={`shrink-0 ${LEVEL_COLORS[log.level] ?? "text-gray-400"}`}
              >
                {log.source}
              </span>
              <span>{log.message}</span>
            </div>
          ))
        )}
        {footer && (
          <div className="text-gray-500 mt-2 pt-2 border-t border-gray-700">
            {footer}
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      {!scrollLocked && logs.length > 0 && (
        <button
          onClick={() => {
            setScrollLocked(true);
            bottomRef.current?.scrollIntoView({ behavior: "smooth" });
          }}
          className="absolute bottom-3 right-3 bg-gray-700 text-gray-300 text-[10px] px-2 py-1 rounded hover:bg-gray-600"
        >
          &darr; Follow
        </button>
      )}
    </div>
  );
}

export type { LogEntry };
