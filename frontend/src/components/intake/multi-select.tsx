"use client";

import { useState } from "react";
import { Check, ChevronsUpDown, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

interface MultiSelectProps {
  options: string[];
  value: string[];
  onChange: (value: string[]) => void;
  placeholder?: string;
  maxSelections?: number;
  renderLabel?: (option: string) => React.ReactNode;
}

export function MultiSelect({
  options,
  value,
  onChange,
  placeholder = "Select options...",
  maxSelections,
  renderLabel,
}: MultiSelectProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  const filtered = search
    ? options.filter((o) => o.toLowerCase().includes(search.toLowerCase()))
    : options;

  function toggle(option: string) {
    if (value.includes(option)) {
      onChange(value.filter((v) => v !== option));
    } else {
      if (maxSelections && value.length >= maxSelections) return;
      onChange([...value, option]);
    }
  }

  function remove(option: string) {
    onChange(value.filter((v) => v !== option));
  }

  return (
    <div className="space-y-1.5">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger
          className={cn(
            "inline-flex items-center justify-between w-full rounded-lg border border-border bg-background px-3 h-8 text-sm hover:bg-muted transition-colors",
            value.length === 0 && "text-muted-foreground",
          )}
        >
          <span className="truncate">
            {value.length === 0
              ? placeholder
              : `${value.length} selected`}
          </span>
          <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 opacity-50 ml-2" />
        </PopoverTrigger>
        <PopoverContent className="w-[var(--popover-trigger-width)] p-0" align="start">
          <div className="p-2 border-b border-border">
            <input
              className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
              placeholder="Search..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="max-h-[200px] overflow-auto p-1">
            {filtered.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-4">No options found</p>
            ) : (
              filtered.map((option) => {
                const selected = value.includes(option);
                const disabled = !selected && !!maxSelections && value.length >= maxSelections;
                return (
                  <button
                    key={option}
                    type="button"
                    onClick={() => toggle(option)}
                    disabled={disabled}
                    className={cn(
                      "flex items-center gap-2 w-full text-left px-2 py-1.5 rounded-sm text-sm transition-colors",
                      selected ? "bg-primary/10 text-primary" : "hover:bg-muted",
                      disabled && "opacity-40 cursor-not-allowed",
                    )}
                  >
                    <div className={cn(
                      "flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border border-border",
                      selected && "bg-primary border-primary",
                    )}>
                      {selected && <Check className="h-3 w-3 text-primary-foreground" />}
                    </div>
                    {renderLabel ? renderLabel(option) : option}
                  </button>
                );
              })
            )}
          </div>
        </PopoverContent>
      </Popover>
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {value.map((v) => (
            <Badge key={v} variant="secondary" className="gap-1 text-xs">
              {v}
              <button type="button" onClick={() => remove(v)} className="ml-0.5 hover:text-destructive">
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}
