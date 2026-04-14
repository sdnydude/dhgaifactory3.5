// =============================================================================
// ENUMS — mirrors registry/cme_endpoints.py
// =============================================================================

export enum CMEProjectStatus {
  INTAKE = "intake",
  PROCESSING = "processing",
  REVIEW = "review",
  AWAITING_REVIEW = "awaiting_review",
  COMPLETE = "complete",
  FAILED = "failed",
  CANCELLED = "cancelled",
  ARCHIVED = "archived",
}

// =============================================================================
// INTAKE SECTIONS — mirrors 10 Pydantic models (47 fields total)
// =============================================================================

export interface SectionA {
  project_name: string;
  therapeutic_area: string[];
  disease_state: string[];
  target_audience_primary: string[];
  target_audience_secondary?: string[];
  target_hcp_types?: string[];
  additional_context?: string;
}

export interface SectionB {
  supporter_name: string;
  supporter_contact_name?: string;
  supporter_contact_email?: string;
  grant_amount_requested?: number;
  grant_submission_deadline?: string;
}

export interface SectionC {
  learning_format: string;
  duration_minutes?: number;
  include_post_test: boolean;
  include_pre_test: boolean;
  faculty_count?: number;
}

export interface SectionD {
  clinical_topics: string[];
  treatment_modalities?: string[];
  patient_population?: string;
  stage_of_disease?: string;
  comorbidities?: string[];
}

export interface SectionE {
  knowledge_gaps?: string[];
  competence_gaps?: string[];
  performance_gaps?: string[];
  gap_evidence_sources?: string[];
  gap_priority?: string;
}

export interface SectionF {
  primary_outcomes?: string[];
  secondary_outcomes?: string[];
  measurement_approach?: string;
  moore_levels_target?: number[];
  follow_up_timeline?: string;
}

export interface SectionG {
  key_messages?: string[];
  required_references?: string[];
  excluded_topics?: string[];
  competitor_products_to_mention?: string[];
  regulatory_considerations?: string;
}

export interface SectionH {
  target_launch_date?: string;
  expiration_date?: string;
  distribution_channels?: string[];
  geo_restrictions?: string[];
  language_requirements?: string[];
}

export interface SectionI {
  accme_compliant: boolean;
  financial_disclosure_required: boolean;
  off_label_discussion: boolean;
  commercial_support_acknowledgment: boolean;
}

export interface SectionJ {
  special_instructions?: string;
  reference_materials?: string[];
  internal_notes?: string;
}

// =============================================================================
// COMPOSITE MODELS
// =============================================================================

export interface IntakeSubmission {
  section_a: SectionA;
  section_b: SectionB;
  section_c: SectionC;
  section_d: SectionD;
  section_e: SectionE;
  section_f: SectionF;
  section_g: SectionG;
  section_h: SectionH;
  section_i: SectionI;
  section_j: SectionJ;
}

export interface CMEProjectCreateResponse {
  project_id: string;
  status: CMEProjectStatus;
  message: string;
  created_at: string;
}

export interface CMEProjectDetail {
  id: string;
  name: string;
  status: CMEProjectStatus;
  current_agent: string | null;
  progress_percent: number;
  intake: Record<string, unknown>;
  intake_version: number;
  created_at: string;
  updated_at: string;
  outputs_available: string[];
  human_review_status: string | null;
}

export interface ExecutionStatus {
  project_id: string;
  status: CMEProjectStatus;
  current_agent: string | null;
  progress_percent: number;
  agents_completed: string[];
  agents_pending: string[];
  errors: Record<string, unknown>[];
  started_at: string | null;
  estimated_completion: string | null;
}

// =============================================================================
// PIPELINE RUNS — mirrors registry/schemas.py PipelineRunRead
// =============================================================================

export type PipelineRunStatus =
  | "processing"
  | "success"
  | "failed"
  | "cancelled";

export type PipelineRunTriggerReason =
  | "initial"
  | "manual"
  | "retry"
  | "auto";

export interface PipelineRun {
  run_id: string;
  project_id: string;
  run_number: number;
  thread_id: string;
  langgraph_run_id: string;
  intake_version_used: number;
  triggered_by: string | null;
  trigger_reason: PipelineRunTriggerReason;
  triggered_at: string;
  completed_at: string | null;
  status: PipelineRunStatus;
  error_message: string | null;
  final_agent: string | null;
  reason: string | null;
  duration_seconds: number | null;
}

export interface PipelineRunListResponse {
  runs: PipelineRun[];
  total: number;
}

export interface RerunRequest {
  reason?: string;
}

export interface AgentOutput {
  agent_name: string;
  output_type: string;
  content: Record<string, unknown>;
  created_at: string;
  quality_score: number | null;
  document_text: string | null;
}

// =============================================================================
// PIPELINE STEPS — 14 steps matching orchestrator.py
// =============================================================================

export interface PipelineStep {
  id: string;
  label: string;
  agent: string;
  order: number;
}

// =============================================================================
// SEARCH — mirrors registry search endpoints
// =============================================================================

export interface SearchResultItem {
  id: string;
  source_table: "cme_documents" | "cme_intake_fields" | "cme_source_references";
  project_id: string;
  title: string;
  snippet: string;
  score: number;
  metadata: Record<string, unknown>;
}

export interface SearchResponse {
  query: string;
  results: SearchResultItem[];
  total: number;
}

export interface HybridSearchRequest {
  query: string;
  project_id?: string;
  source_tables?: string[];
  limit?: number;
  fulltext_weight?: number;
  vector_weight?: number;
}

// =============================================================================
// INTAKE PREFILL
// =============================================================================

export type PrefillConfidence = "high" | "medium" | "low";

export interface PrefillResponse {
  prefill_sections: {
    section_b?: Partial<SectionB>;
    section_c?: Partial<SectionC>;
    section_d?: Partial<SectionD>;
    section_e?: Partial<SectionE>;
    section_f?: Partial<SectionF>;
    section_g?: Partial<SectionG>;
    section_h?: Partial<SectionH>;
  };
  research_summary: string;
  confidence: Record<string, PrefillConfidence>;
}

export const PIPELINE_STEPS: PipelineStep[] = [
  { id: "research", label: "Research & Literature", agent: "research_agent", order: 1 },
  { id: "clinical", label: "Clinical Practice", agent: "clinical_practice_agent", order: 2 },
  { id: "gap_analysis", label: "Gap Analysis", agent: "gap_analysis_agent", order: 3 },
  { id: "learning_objectives", label: "Learning Objectives", agent: "learning_objectives_agent", order: 4 },
  { id: "needs_assessment", label: "Needs Assessment", agent: "needs_assessment_agent", order: 5 },
  { id: "prose_quality_1", label: "Prose QA Pass 1", agent: "prose_quality_agent", order: 6 },
  { id: "human_review_1", label: "Human Review 1", agent: "human_review", order: 7 },
  { id: "curriculum", label: "Curriculum Design", agent: "curriculum_design_agent", order: 8 },
  { id: "protocol", label: "Research Protocol", agent: "research_protocol_agent", order: 9 },
  { id: "marketing", label: "Marketing Plan", agent: "marketing_plan_agent", order: 10 },
  { id: "grant_writer", label: "Grant Writing", agent: "grant_writer_agent", order: 11 },
  { id: "prose_quality_2", label: "Prose QA Pass 2", agent: "prose_quality_agent", order: 12 },
  { id: "compliance", label: "Compliance Review", agent: "compliance_review_agent", order: 13 },
  { id: "final_review", label: "Final Review", agent: "human_review", order: 14 },
];
