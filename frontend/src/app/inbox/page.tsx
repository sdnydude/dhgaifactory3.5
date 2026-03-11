"use client";

import { Header } from "@/components/dhg/header";
import { InboxList } from "@/components/agent-inbox/inbox-list";
import { useState } from "react";

export default function InboxPage() {
  const [graphId, setGraphId] = useState("needs_assessment");

  return (
    <div className="flex flex-col h-dvh bg-background">
      <Header graphId={graphId} onGraphChange={setGraphId} />
      <main className="flex-1 overflow-auto">
        <div className="mx-auto max-w-3xl px-6 py-8">
          <InboxList />
        </div>
      </main>
    </div>
  );
}
