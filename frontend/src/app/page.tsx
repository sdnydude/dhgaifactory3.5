"use client";

import { useState } from "react";
import { Header } from "@/components/dhg/header";
import { Assistant } from "@/components/dhg/assistant";

export default function Home() {
  const [graphId, setGraphId] = useState("needs_assessment");

  return (
    <div className="flex flex-col h-dvh bg-background">
      <Header graphId={graphId} onGraphChange={setGraphId} />
      <main className="flex-1 overflow-hidden">
        <Assistant key={graphId} graphId={graphId} />
      </main>
    </div>
  );
}
