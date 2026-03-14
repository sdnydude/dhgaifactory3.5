"use client";

import type { ServiceHealth } from "@/types/monitoring";
import { Skeleton } from "@/components/ui/skeleton";

interface ServiceHealthGridProps {
  services: ServiceHealth[];
  loading: boolean;
}

const statusStyles = {
  healthy: {
    dot: "bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.4)] animate-pulse",
    label: "bg-green-500/10 text-green-600 dark:text-green-400",
  },
  degraded: {
    dot: "bg-dhg-orange shadow-[0_0_6px_rgba(247,126,45,0.4)] animate-pulse",
    label: "bg-dhg-orange/10 text-dhg-orange",
  },
  down: {
    dot: "bg-destructive shadow-[0_0_6px_rgba(239,68,68,0.4)]",
    label: "bg-destructive/10 text-destructive",
  },
};

export function ServiceHealthGrid({ services, loading }: ServiceHealthGridProps) {
  if (loading || services.length === 0) {
    return (
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-40 rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      {services.map((svc) => {
        const styles = statusStyles[svc.status];
        return (
          <div
            key={svc.name}
            className="rounded-xl border bg-card p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
          >
            <div className="mb-3 flex items-center justify-between">
              <span className="text-sm font-semibold">{svc.name}</span>
              <span className={`h-2.5 w-2.5 rounded-full ${styles.dot}`} />
            </div>
            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Port</span>
                <span className="font-mono font-medium">{svc.port}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Response</span>
                <span className="font-mono font-medium">
                  {svc.status === "down" ? "—" : `${svc.responseMs}ms`}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Purpose</span>
                <span className="font-normal">{svc.description}</span>
              </div>
            </div>
            <span
              className={`mt-3 inline-block rounded-md px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide ${styles.label}`}
            >
              {svc.status}
            </span>
          </div>
        );
      })}
    </div>
  );
}
