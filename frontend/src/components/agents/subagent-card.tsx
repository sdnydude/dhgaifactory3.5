"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface SubagentCardProps {
  name: string;
  status: string;
  tokens?: number;
  elapsed?: string;
}

export function SubagentCard({ name, status, tokens, elapsed }: SubagentCardProps) {
  return (
    <Card>
      <CardContent className="py-3 px-4 flex items-center justify-between">
        <div>
          <p className="text-xs font-medium">{name}</p>
          <div className="flex items-center gap-2 mt-1 text-[10px] text-muted-foreground">
            {tokens !== undefined && <span>{tokens.toLocaleString()} tokens</span>}
            {elapsed && <span>{elapsed}</span>}
          </div>
        </div>
        <Badge variant="outline" className="text-[9px]">{status}</Badge>
      </CardContent>
    </Card>
  );
}
