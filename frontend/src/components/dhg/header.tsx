"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Inbox, Sparkles } from "lucide-react";
import { GraphSelector } from "./graph-selector";

interface HeaderProps {
  graphId?: string;
  onGraphChange?: (graphId: string) => void;
}

export function Header({ graphId, onGraphChange }: HeaderProps) {
  const pathname = usePathname();

  return (
    <header className="flex items-center justify-between border-b border-border bg-card px-6 py-3">
      <div className="flex items-center gap-3">
        <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          <div className="h-8 w-8 rounded-lg bg-dhg-purple flex items-center justify-center">
            <span className="text-white font-bold text-sm">AI</span>
          </div>
          <div>
            <h1 className="text-sm font-semibold text-foreground leading-none">
              DHG AI Factory
            </h1>
            <p className="text-[10px] text-muted-foreground">
              AI Agents In Tune With You
            </p>
          </div>
        </Link>
        {graphId && onGraphChange && (
          <>
            <div className="h-6 w-px bg-border mx-2" />
            <GraphSelector value={graphId} onChange={onGraphChange} />
          </>
        )}
      </div>
      <div className="flex items-center gap-3">
        <Link
          href="/inbox"
          className={`flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-md transition-colors ${
            pathname === "/inbox"
              ? "bg-dhg-purple text-white"
              : "text-muted-foreground hover:text-foreground hover:bg-muted"
          }`}
        >
          <Inbox className="h-3.5 w-3.5" />
          Review Inbox
        </Link>
        <Link
          href="/studio"
          className={`flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-md transition-colors ${
            pathname === "/studio"
              ? "bg-dhg-purple text-white"
              : "text-muted-foreground hover:text-foreground hover:bg-muted"
          }`}
        >
          <Sparkles className="h-3.5 w-3.5" />
          Studio
        </Link>
        <div className="h-4 w-px bg-border" />
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            LangGraph Server
          </span>
          <span className="inline-block h-2 w-2 rounded-full bg-green-500" />
        </div>
      </div>
    </header>
  );
}
