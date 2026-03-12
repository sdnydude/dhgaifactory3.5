"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  FolderKanban,
  Inbox,
  MessageSquare,
  Activity,
  Sparkles,
  PanelLeftClose,
  PanelLeft,
  Moon,
  Sun,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import { useAppStore } from "@/stores/app-store";
import { useTheme } from "@/hooks/use-theme";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/projects", icon: FolderKanban, label: "Projects", badgeKey: "processing" as const },
  { href: "/inbox", icon: Inbox, label: "Inbox", badgeKey: "inbox" as const },
  { href: "/chat", icon: MessageSquare, label: "Chat", badgeKey: null },
  { href: "/agents", icon: Activity, label: "Agents", badgeKey: null },
  { href: "/studio", icon: Sparkles, label: "Studio", badgeKey: null },
];

function NavLink({
  href,
  active,
  collapsed,
  icon: Icon,
  label,
  badge,
}: {
  href: string;
  active: boolean;
  collapsed: boolean;
  icon: typeof FolderKanban;
  label: string;
  badge: number;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "bg-primary text-primary-foreground"
          : "text-sidebar-foreground hover:bg-sidebar-accent",
        collapsed && "justify-center px-0",
      )}
    >
      <Icon className="h-4 w-4 shrink-0" />
      {!collapsed && (
        <>
          <span className="flex-1">{label}</span>
          {badge > 0 && (
            <Badge variant="secondary" className="h-5 min-w-[20px] justify-center text-[10px] px-1.5">
              {badge}
            </Badge>
          )}
        </>
      )}
    </Link>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const collapsed = useAppStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useAppStore((s) => s.toggleSidebar);
  const badgeCounts = useAppStore((s) => s.badgeCounts);
  const { darkMode, toggleDarkMode } = useTheme();
  const [cloudStatus, setCloudStatus] = useState<"ok" | "down" | "checking">("checking");

  useEffect(() => {
    let active = true;
    const check = () => {
      fetch("/api/langgraph/ok")
        .then((r) => { if (active) setCloudStatus(r.ok ? "ok" : "down"); })
        .catch(() => { if (active) setCloudStatus("down"); });
    };
    check();
    const interval = setInterval(check, 60_000);
    return () => { active = false; clearInterval(interval); };
  }, []);

  return (
    <aside
      className={cn(
        "flex flex-col border-r border-border bg-sidebar h-full transition-all duration-200",
        collapsed ? "w-[60px]" : "w-[200px]",
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-2 px-3 py-4 border-b border-border min-h-[56px]">
        <Link href="/projects" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          <div className="h-8 w-8 shrink-0 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-primary-foreground font-bold text-sm">AI</span>
          </div>
          {!collapsed && (
            <div className="overflow-hidden">
              <h1 className="text-sm font-semibold text-sidebar-foreground leading-none whitespace-nowrap">
                DHG AI Factory
              </h1>
              <p className="text-[10px] text-muted-foreground whitespace-nowrap">
                AI Agents In Tune With You
              </p>
            </div>
          )}
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-2 space-y-1 px-2">
        {NAV_ITEMS.map((item) => {
          const active = pathname.startsWith(item.href);
          const badge = item.badgeKey ? badgeCounts[item.badgeKey] : 0;

          if (collapsed) {
            return (
              <Tooltip key={item.href}>
                <TooltipTrigger className="w-full">
                  <NavLink href={item.href} active={active} collapsed icon={item.icon} label={item.label} badge={badge} />
                </TooltipTrigger>
                <TooltipContent side="right" className="flex items-center gap-2">
                  {item.label}
                  {badge > 0 && (
                    <Badge variant="secondary" className="h-5 text-[10px]">
                      {badge}
                    </Badge>
                  )}
                </TooltipContent>
              </Tooltip>
            );
          }

          return (
            <NavLink key={item.href} href={item.href} active={active} collapsed={false} icon={item.icon} label={item.label} badge={badge} />
          );
        })}
      </nav>

      {/* LangGraph Status */}
      <div className={cn("px-3 py-2 border-t border-border", collapsed && "px-0 flex justify-center")}>
        {collapsed ? (
          <Tooltip>
            <TooltipTrigger className="inline-flex">
              <span className={cn(
                "inline-block h-2 w-2 rounded-full",
                cloudStatus === "ok" ? "bg-green-500" : cloudStatus === "down" ? "bg-red-500" : "bg-yellow-500 animate-pulse",
              )} />
            </TooltipTrigger>
            <TooltipContent side="right">LangGraph Cloud {cloudStatus === "ok" ? "Connected" : cloudStatus === "down" ? "Unreachable" : "Checking..."}</TooltipContent>
          </Tooltip>
        ) : (
          <div className="flex items-center gap-2">
            <span className={cn(
              "inline-block h-2 w-2 rounded-full",
              cloudStatus === "ok" ? "bg-green-500" : cloudStatus === "down" ? "bg-red-500" : "bg-yellow-500 animate-pulse",
            )} />
            <span className="text-xs text-muted-foreground">
              LangGraph {cloudStatus === "ok" ? "Cloud" : cloudStatus === "down" ? "Down" : "..."}
            </span>
          </div>
        )}
      </div>

      {/* Bottom controls */}
      <div className={cn("border-t border-border p-2 flex gap-1", collapsed ? "flex-col items-center" : "")}>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={toggleDarkMode}
          aria-label="Toggle dark mode"
        >
          {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={toggleSidebar}
          aria-label="Toggle sidebar"
        >
          {collapsed ? (
            <PanelLeft className="h-4 w-4" />
          ) : (
            <PanelLeftClose className="h-4 w-4" />
          )}
        </Button>
      </div>
    </aside>
  );
}
