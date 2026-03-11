"use client";

import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { GRAPHS, type GraphInfo } from "@/lib/graphs";

interface GraphSelectorProps {
  value: string;
  onChange: (graphId: string) => void;
}

export function GraphSelector({ value, onChange }: GraphSelectorProps) {
  const agents = GRAPHS.filter((g) => g.category === "agent");
  const orchestrators = GRAPHS.filter((g) => g.category === "orchestrator");

  const selected = GRAPHS.find((g) => g.id === value);

  return (
    <div className="flex items-center gap-2">
      <Select value={value} onValueChange={(val) => { if (val !== null) onChange(val); }}>
        <SelectTrigger className="w-[280px]">
          <SelectValue placeholder="Select a graph" />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            <SelectLabel>Orchestrators</SelectLabel>
            {orchestrators.map((g) => (
              <SelectItem key={g.id} value={g.id}>
                <span className="flex items-center gap-2">
                  {g.label}
                  <Badge
                    variant="secondary"
                    className="text-[10px] px-1 py-0"
                  >
                    pipeline
                  </Badge>
                </span>
              </SelectItem>
            ))}
          </SelectGroup>
          <SelectGroup>
            <SelectLabel>Individual Agents</SelectLabel>
            {agents.map((g) => (
              <SelectItem key={g.id} value={g.id}>
                {g.label}
              </SelectItem>
            ))}
          </SelectGroup>
        </SelectContent>
      </Select>
      {selected && (
        <span className="text-xs text-muted-foreground hidden sm:inline">
          {selected.description}
        </span>
      )}
    </div>
  );
}
