export type Role = "admin" | "operations" | "finance" | "editor" | "viewer";

export interface RoutePermission {
  path: string;
  label: string;
  section: "work" | "observe" | "manage";
  roles: Role[];
}

export const ROUTE_PERMISSIONS: RoutePermission[] = [
  // Work section
  { path: "/projects", label: "Projects", section: "work", roles: ["admin", "operations", "finance", "editor", "viewer"] },
  { path: "/inbox", label: "Inbox", section: "work", roles: ["admin", "operations", "editor", "viewer"] },
  { path: "/chat", label: "Chat", section: "work", roles: ["admin", "operations", "editor"] },
  { path: "/search", label: "Search", section: "work", roles: ["admin", "operations", "editor"] },
  // Observe section
  { path: "/agents", label: "Agents", section: "observe", roles: ["admin", "operations"] },
  { path: "/dashboards", label: "Dashboards", section: "observe", roles: ["admin", "operations", "finance"] },
  { path: "/monitoring", label: "Monitoring", section: "observe", roles: ["admin", "operations"] },
  { path: "/studio", label: "Studio", section: "observe", roles: ["admin", "operations"] },
  // Manage section
  { path: "/admin", label: "Admin Console", section: "manage", roles: ["admin"] },
  { path: "/admin/reporting", label: "Reporting", section: "manage", roles: ["admin"] },
];

export const SECTION_LABELS: Record<string, string> = {
  work: "Work",
  observe: "Observe",
  manage: "Manage",
};

export function getVisibleRoutes(roles: Role[]): RoutePermission[] {
  return ROUTE_PERMISSIONS.filter((route) =>
    route.roles.some((r) => roles.includes(r))
  );
}

export function canAccessRoute(roles: Role[], path: string): boolean {
  const route = ROUTE_PERMISSIONS.find((r) => path.startsWith(r.path));
  if (!route) return true;
  return route.roles.some((r) => roles.includes(r));
}

export function getVisibleSections(roles: Role[]): string[] {
  const visible = getVisibleRoutes(roles);
  return [...new Set(visible.map((r) => r.section))];
}
