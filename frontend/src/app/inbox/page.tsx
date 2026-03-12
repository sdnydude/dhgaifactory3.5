"use client";

import { InboxList } from "@/components/agent-inbox/inbox-list";

export default function InboxPage() {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-3 border-b border-border px-6 py-3">
        <h2 className="text-sm font-semibold text-foreground">Review Inbox</h2>
      </div>
      <div className="flex-1 overflow-auto">
        <div className="mx-auto max-w-3xl px-6 py-8">
          <InboxList />
        </div>
      </div>
    </div>
  );
}
