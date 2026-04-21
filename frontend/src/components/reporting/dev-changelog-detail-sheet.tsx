"use client";

import * as React from "react";
import { ExternalLink, Loader2 } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import { useDevChangelogStore } from "@/stores/dev-changelog-store";
import {
  getDevChangelog,
  patchDevChangelog,
  type DevChangelogCategory,
  type DevChangelogEntry,
  type DevChangelogPatch,
  type DevChangelogStatus,
} from "@/lib/devChangelogApi";

const REPO_COMMIT_BASE =
  "https://github.com/sdnydude/dhgaifactory3.5/commit";

const CATEGORY_TONE: Record<DevChangelogCategory, string> = {
  feature: "border-emerald-500/40 text-emerald-700 dark:text-emerald-300",
  infra: "border-sky-500/40 text-sky-700 dark:text-sky-300",
  fix: "border-amber-500/40 text-amber-700 dark:text-amber-300",
  refactor: "border-violet-500/40 text-violet-700 dark:text-violet-300",
  docs: "border-zinc-500/40 text-zinc-600 dark:text-zinc-300",
  debt: "border-rose-500/40 text-rose-700 dark:text-rose-300",
};

const STATUS_TONE: Record<DevChangelogStatus, string> = {
  shipped:
    "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 ring-emerald-500/30",
  in_progress:
    "bg-amber-500/15 text-amber-700 dark:text-amber-300 ring-amber-500/30",
  backlog:
    "bg-zinc-500/15 text-zinc-700 dark:text-zinc-300 ring-zinc-500/30",
  abandoned:
    "bg-rose-500/15 text-rose-600 dark:text-rose-300 ring-rose-500/30",
};

const STATUS_LABEL: Record<DevChangelogStatus, string> = {
  shipped: "Shipped",
  in_progress: "In progress",
  backlog: "Backlog",
  abandoned: "Abandoned",
};

const DECLARED_OPTIONS: Array<{ value: ""; label: string } | { value: DevChangelogStatus; label: string }> = [
  { value: "", label: "— (use detected)" },
  { value: "shipped", label: "Shipped" },
  { value: "in_progress", label: "In progress" },
  { value: "backlog", label: "Backlog" },
  { value: "abandoned", label: "Abandoned" },
];

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

interface Draft {
  declared_status: DevChangelogStatus | null;
  key_insight: string;
  notes: string;
  priority: string; // stored as string for controlled input; parsed on save
  locked: boolean;
}

function entryToDraft(entry: DevChangelogEntry): Draft {
  return {
    declared_status: entry.declared_status,
    key_insight: entry.key_insight ?? "",
    notes: entry.notes ?? "",
    priority: entry.priority != null ? String(entry.priority) : "",
    locked: entry.locked,
  };
}

function computePatch(entry: DevChangelogEntry, draft: Draft): DevChangelogPatch {
  const patch: DevChangelogPatch = {};

  if (draft.declared_status !== entry.declared_status) {
    patch.declared_status = draft.declared_status;
  }

  const nextInsight = draft.key_insight.trim() === "" ? null : draft.key_insight;
  if (nextInsight !== entry.key_insight) {
    patch.key_insight = nextInsight;
  }

  const nextNotes = draft.notes.trim() === "" ? null : draft.notes;
  if (nextNotes !== entry.notes) {
    patch.notes = nextNotes;
  }

  const trimmed = draft.priority.trim();
  const nextPriority = trimmed === "" ? null : Number(trimmed);
  if (nextPriority !== entry.priority) {
    patch.priority = nextPriority;
  }

  if (draft.locked !== entry.locked) {
    patch.locked = draft.locked;
  }

  return patch;
}

function Field({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="space-y-1">
      <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
        {label}
      </p>
      <div
        className={cn(
          "text-[12px] text-foreground",
          mono && "font-mono tabular-nums",
        )}
      >
        {value}
      </div>
    </div>
  );
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
      {children}
    </p>
  );
}

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
      {children}
    </h3>
  );
}

function EditorialForm({ entry }: { entry: DevChangelogEntry }) {
  const updateEntry = useDevChangelogStore((s) => s.updateEntry);
  const [draft, setDraft] = React.useState<Draft>(() => entryToDraft(entry));
  const [saving, setSaving] = React.useState(false);
  const [saveError, setSaveError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setDraft(entryToDraft(entry));
    setSaveError(null);
  }, [entry.id, entry.declared_status, entry.key_insight, entry.notes, entry.priority, entry.locked]);

  const patch = computePatch(entry, draft);
  const isDirty = Object.keys(patch).length > 0;

  const priorityError =
    draft.priority.trim() !== "" && Number.isNaN(Number(draft.priority))
      ? "Must be a number"
      : null;

  async function handleSave() {
    if (!isDirty || priorityError) return;
    setSaving(true);
    setSaveError(null);
    try {
      const updated = await patchDevChangelog(entry.slug, patch);
      updateEntry(updated);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  function handleDiscard() {
    setDraft(entryToDraft(entry));
    setSaveError(null);
  }

  return (
    <div className="space-y-4 rounded-lg border border-border p-4">
      {/* Declared status */}
      <div className="space-y-1.5">
        <FieldLabel>Declared status</FieldLabel>
        <select
          value={draft.declared_status ?? ""}
          onChange={(e) =>
            setDraft((d) => ({
              ...d,
              declared_status:
                e.target.value === ""
                  ? null
                  : (e.target.value as DevChangelogStatus),
            }))
          }
          disabled={saving}
          className="h-8 w-full rounded-md border border-input bg-background px-2 text-[12px] transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-50"
        >
          {DECLARED_OPTIONS.map((opt) => (
            <option key={opt.value || "detected"} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <p className="text-[10px] text-muted-foreground">
          Overrides the agent&apos;s detected status. Empty falls back to detected.
        </p>
      </div>

      {/* Priority */}
      <div className="space-y-1.5">
        <FieldLabel>Priority</FieldLabel>
        <Input
          type="number"
          inputMode="numeric"
          value={draft.priority}
          onChange={(e) => setDraft((d) => ({ ...d, priority: e.target.value }))}
          disabled={saving}
          placeholder="—"
          className="h-8 max-w-[120px] text-[12px]"
          aria-invalid={!!priorityError}
        />
        {priorityError && (
          <p className="text-[10px] text-destructive">{priorityError}</p>
        )}
      </div>

      {/* Key insight */}
      <div className="space-y-1.5">
        <FieldLabel>Key insight</FieldLabel>
        <Textarea
          value={draft.key_insight}
          onChange={(e) =>
            setDraft((d) => ({ ...d, key_insight: e.target.value }))
          }
          disabled={saving}
          placeholder="The one-sentence editorial reason this epic exists."
          rows={3}
          className="text-[13px] leading-relaxed font-serif-body"
        />
      </div>

      {/* Notes */}
      <div className="space-y-1.5">
        <FieldLabel>Notes</FieldLabel>
        <Textarea
          value={draft.notes}
          onChange={(e) => setDraft((d) => ({ ...d, notes: e.target.value }))}
          disabled={saving}
          placeholder="Context, gotchas, follow-ups."
          rows={5}
          className="text-[12px] leading-relaxed"
        />
      </div>

      {/* Locked */}
      <div className="flex items-center justify-between gap-3">
        <div className="space-y-0.5">
          <FieldLabel>Locked</FieldLabel>
          <p className="text-[10px] text-muted-foreground">
            When on, the nightly agent will not overwrite editorial fields.
          </p>
        </div>
        <Switch
          checked={draft.locked}
          onCheckedChange={(v) => setDraft((d) => ({ ...d, locked: v }))}
          disabled={saving}
        />
      </div>

      {/* Last edit timestamp */}
      <div className="pt-1">
        <Field
          label="Last human edit"
          value={formatDateTime(entry.last_human_edit_at)}
          mono
        />
      </div>

      {/* Save bar */}
      {(isDirty || saveError) && (
        <div className="space-y-2 border-t border-border pt-3">
          {saveError && (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-[11px] text-destructive">
              {saveError}
            </div>
          )}
          {isDirty && (
            <div className="flex items-center justify-between gap-2">
              <p className="text-[10px] text-muted-foreground">
                {Object.keys(patch).length} unsaved{" "}
                {Object.keys(patch).length === 1 ? "change" : "changes"}
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={handleDiscard}
                  disabled={saving}
                >
                  Discard
                </Button>
                <Button
                  size="sm"
                  className="h-7 text-xs"
                  onClick={handleSave}
                  disabled={saving || !!priorityError}
                >
                  {saving && <Loader2 className="h-3 w-3 animate-spin" />}
                  Save
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function DetailBody({ entry }: { entry: DevChangelogEntry }) {
  const displayStatus = entry.declared_status ?? entry.detected_status;
  return (
    <div className="flex flex-col gap-6 px-6 pb-10">
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.08em] ring-1 ring-inset",
            STATUS_TONE[displayStatus],
          )}
        >
          {STATUS_LABEL[displayStatus]}
        </span>
        <span
          className={cn(
            "inline-flex items-center rounded border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.12em]",
            CATEGORY_TONE[entry.category],
          )}
        >
          {entry.category}
        </span>
        {entry.locked && (
          <span className="inline-flex items-center gap-1 rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.12em] text-muted-foreground">
            🔒 Locked
          </span>
        )}
      </div>

      <section className="space-y-3">
        <SectionHeader>Agent-detected</SectionHeader>
        <div className="grid grid-cols-2 gap-4 rounded-lg border border-border bg-muted/20 p-4">
          <Field label="Slug" value={entry.slug} mono />
          <Field
            label="Detected status"
            value={STATUS_LABEL[entry.detected_status]}
          />
          <Field label="Window start" value={formatDate(entry.window_start)} mono />
          <Field label="Window end" value={formatDate(entry.window_end)} mono />
          <Field label="Commits" value={entry.commit_count} mono />
          <Field label="Source" value={entry.source} />
          <Field
            label="Detected at"
            value={formatDateTime(entry.detected_at)}
            mono
          />
          <Field
            label="Last agent run"
            value={formatDateTime(entry.last_agent_run_at)}
            mono
          />
        </div>
      </section>

      <section className="space-y-3">
        <SectionHeader>Editorial</SectionHeader>
        <EditorialForm entry={entry} />
      </section>

      <section className="space-y-3">
        <SectionHeader>Commits ({entry.commits.length})</SectionHeader>
        {entry.commits.length === 0 ? (
          <p className="text-[12px] text-muted-foreground">
            No commits recorded in this window.
          </p>
        ) : (
          <ol className="space-y-2">
            {entry.commits.map((commit) => {
              const shortSha = commit.sha.slice(0, 7);
              return (
                <li
                  key={commit.sha}
                  className="rounded-md border border-border bg-background p-3 transition-colors hover:bg-muted/40"
                >
                  <a
                    href={`${REPO_COMMIT_BASE}/${commit.sha}`}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="flex items-start justify-between gap-3"
                  >
                    <div className="min-w-0 flex-1 space-y-1">
                      <p className="truncate text-[12px] font-medium leading-snug text-foreground">
                        {commit.subject}
                      </p>
                      <div className="flex items-center gap-2 font-mono text-[10px] tabular-nums text-muted-foreground">
                        <span>{shortSha}</span>
                        <span>·</span>
                        <span>{formatDate(commit.date)}</span>
                        {commit.author && (
                          <>
                            <span>·</span>
                            <span className="truncate">{commit.author}</span>
                          </>
                        )}
                      </div>
                    </div>
                    <ExternalLink className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  </a>
                </li>
              );
            })}
          </ol>
        )}
      </section>
    </div>
  );
}

export function DevChangelogDetailSheet() {
  const selectedSlug = useDevChangelogStore((s) => s.selectedSlug);
  const selectRow = useDevChangelogStore((s) => s.selectRow);
  const updateEntry = useDevChangelogStore((s) => s.updateEntry);
  const entry = useDevChangelogStore((s) =>
    s.selectedSlug
      ? s.entries.find((e) => e.slug === s.selectedSlug) ?? null
      : null,
  );

  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!selectedSlug) {
      setError(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    getDevChangelog(selectedSlug)
      .then((result) => {
        if (cancelled) return;
        updateEntry(result);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load entry");
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedSlug, updateEntry]);

  const open = !!selectedSlug;

  return (
    <Sheet open={open} onOpenChange={(v) => !v && selectRow(null)}>
      <SheetContent className="w-[560px] sm:max-w-none overflow-y-auto">
        <SheetHeader className="border-b border-border">
          <SheetTitle className="pr-8 text-base font-semibold leading-snug">
            {entry?.epic ?? (loading ? "Loading…" : selectedSlug ?? "")}
          </SheetTitle>
          {entry && (
            <p className="font-mono text-[11px] text-muted-foreground">
              {entry.slug}
            </p>
          )}
        </SheetHeader>

        {loading && !entry && (
          <div className="flex items-center gap-2 px-6 py-8 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading entry…
          </div>
        )}

        {error && (
          <div className="mx-6 rounded-md border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        )}

        {entry && <DetailBody entry={entry} />}
      </SheetContent>
    </Sheet>
  );
}
