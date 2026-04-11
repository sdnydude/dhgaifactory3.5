"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Loader2, Sparkles, CheckCheck, Trash2 } from "lucide-react";
import { SectionNav, SECTIONS } from "./section-nav";
import { SectionABasics } from "./section-a-basics";
import { SectionBSupporter } from "./section-b-supporter";
import { SectionCEducational } from "./section-c-educational";
import { SectionDClinical } from "./section-d-clinical";
import { SectionEGaps } from "./section-e-gaps";
import { SectionFOutcomes } from "./section-f-outcomes";
import { SectionGContent } from "./section-g-content";
import { SectionHLogistics } from "./section-h-logistics";
import { SectionICompliance } from "./section-i-compliance";
import { SectionJAdditional } from "./section-j-additional";
import type { IntakeSubmission } from "@/types/cme";
import * as registryApi from "@/lib/registryApi";
import { useIntakeStore } from "@/stores/intake-store";

function isSectionComplete(intake: IntakeSubmission, sectionId: string): boolean {
  switch (sectionId) {
    case "a": {
      const a = intake.section_a;
      return a.project_name.length >= 5 && a.therapeutic_area.length > 0 && a.disease_state.length > 0 && a.target_audience_primary.length >= 1;
    }
    case "b": return !!intake.section_b.supporter_name;
    case "c": return !!intake.section_c.learning_format;
    case "d": return intake.section_d.clinical_topics.length > 0;
    case "e": return (intake.section_e.knowledge_gaps?.length ?? 0) > 0;
    case "f": return (intake.section_f.primary_outcomes?.length ?? 0) > 0;
    case "g": return (intake.section_g.key_messages?.length ?? 0) > 0;
    case "h": return !!intake.section_h.target_launch_date;
    case "i": return true;
    case "j": return !!intake.section_j.special_instructions;
    default: return false;
  }
}

export function IntakeForm() {
  const router = useRouter();
  const {
    intake,
    updateIntake,
    activeSection,
    setActiveSection,
    reset,
    prefillStatus,
    researchSummary,
    prefillConfidence,
    applyPrefill,
    acceptSection,
    clearSection,
    acceptAll,
    clearAll,
  } = useIntakeStore();
  const [saving, setSaving] = useState(false);
  const [prefilling, setPrefilling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const completedSections = useMemo(() => {
    const set = new Set<string>();
    for (const s of SECTIONS) {
      if (isSectionComplete(intake, s.id)) set.add(s.id);
    }
    return set;
  }, [intake]);

  const canSave =
    intake.section_a.project_name.length >= 5 &&
    intake.section_a.therapeutic_area.length > 0 &&
    intake.section_a.disease_state.length > 0 &&
    intake.section_a.target_audience_primary.length >= 1;

  const hasPrefilled = Object.values(prefillStatus).some((s) => s === "prefilled");

  async function handlePrefill() {
    setPrefilling(true);
    setError(null);
    try {
      const result = await registryApi.prefillIntake(intake.section_a);
      applyPrefill(
        result.prefill_sections,
        result.research_summary,
        result.confidence,
      );
      setActiveSection("b");
    } catch (e) {
      setError("Prefill unavailable \u2014 you can fill sections manually.");
    } finally {
      setPrefilling(false);
    }
  }

  async function handleSave(startPipeline: boolean) {
    setSaving(true);
    setError(null);
    try {
      const result = await registryApi.createProject(intake);
      if (startPipeline) {
        registryApi.startPipeline(result.project_id).catch((e) => {
          console.error("Pipeline start failed:", e);
        });
      }
      reset();
      router.push(`/projects/${result.project_id}`);
    } catch (e) {
      setError((e as Error).message);
      setSaving(false);
    }
  }

  function renderSection() {
    switch (activeSection) {
      case "a": return <SectionABasics data={intake.section_a} onChange={(d) => updateIntake((p) => ({ ...p, section_a: d }))} />;
      case "b": return <SectionBSupporter data={intake.section_b} onChange={(d) => updateIntake((p) => ({ ...p, section_b: d }))} />;
      case "c": return <SectionCEducational data={intake.section_c} onChange={(d) => updateIntake((p) => ({ ...p, section_c: d }))} />;
      case "d": return <SectionDClinical data={intake.section_d} onChange={(d) => updateIntake((p) => ({ ...p, section_d: d }))} />;
      case "e": return <SectionEGaps data={intake.section_e} onChange={(d) => updateIntake((p) => ({ ...p, section_e: d }))} />;
      case "f": return <SectionFOutcomes data={intake.section_f} onChange={(d) => updateIntake((p) => ({ ...p, section_f: d }))} />;
      case "g": return <SectionGContent data={intake.section_g} onChange={(d) => updateIntake((p) => ({ ...p, section_g: d }))} />;
      case "h": return <SectionHLogistics data={intake.section_h} onChange={(d) => updateIntake((p) => ({ ...p, section_h: d }))} />;
      case "i": return <SectionICompliance data={intake.section_i} onChange={(d) => updateIntake((p) => ({ ...p, section_i: d }))} />;
      case "j": return <SectionJAdditional data={intake.section_j} onChange={(d) => updateIntake((p) => ({ ...p, section_j: d }))} />;
      default: return null;
    }
  }

  return (
    <div className="flex h-full">
      <SectionNav
        activeSection={activeSection}
        onSelect={setActiveSection}
        completedSections={completedSections}
        prefillStatus={prefillStatus}
        prefillConfidence={prefillConfidence}
        onAcceptSection={acceptSection}
        onClearSection={clearSection}
      />
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Prefill banner — entrance animation via tw-animate-css */}
        {hasPrefilled && (
          <div
            role="status"
            className="mx-6 mt-4 rounded-md border border-primary/20 bg-primary/5 p-3 flex items-center gap-3 animate-in fade-in slide-in-from-top-2 duration-300"
          >
            <Sparkles className="h-4 w-4 text-primary shrink-0" aria-hidden="true" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground">
                AI Draft Ready
              </p>
              {researchSummary && (
                <p className="text-xs text-muted-foreground truncate">
                  {researchSummary}
                </p>
              )}
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="text-green-500 hover:bg-muted"
              onClick={acceptAll}
              aria-label="Accept all AI-drafted sections"
            >
              <CheckCheck className="h-3.5 w-3.5 mr-1" />
              Accept All
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-muted-foreground hover:text-destructive hover:bg-destructive/10"
              onClick={clearAll}
              aria-label="Clear all AI-drafted sections"
            >
              <Trash2 className="h-3.5 w-3.5 mr-1" />
              Clear All
            </Button>
          </div>
        )}

        <div className="flex-1 overflow-auto p-6 max-w-2xl">
          {renderSection()}
        </div>

        {error && (
          <div role="alert" className="mx-6 mb-3 rounded-md bg-destructive/10 text-destructive text-sm p-3">
            {error}
          </div>
        )}

        <div className="border-t border-border px-6 py-3 flex items-center gap-3">
          <Button variant="outline" onClick={() => router.push("/projects")} disabled={saving || prefilling}>
            Cancel
          </Button>
          <Button
            variant="outline"
            onClick={handlePrefill}
            disabled={!canSave || prefilling || saving}
            className="border-primary/30 text-primary hover:bg-primary/5"
          >
            {prefilling ? (
              <>
                <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                Researching {intake.section_a.disease_state.join(", ")}...
              </>
            ) : (
              <>
                <Sparkles className="h-3.5 w-3.5 mr-1.5" />
                Research &amp; Prefill
              </>
            )}
          </Button>
          <div className="flex-1" />
          <Button variant="secondary" onClick={() => handleSave(false)} disabled={!canSave || saving || prefilling}>
            {saving ? "Saving..." : "Save Draft"}
          </Button>
          <Button onClick={() => handleSave(true)} disabled={!canSave || saving || prefilling}>
            {saving ? "Starting..." : "Save & Start Pipeline"}
          </Button>
        </div>
      </div>
    </div>
  );
}
