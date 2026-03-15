export interface ReviewComment {
  id: string;
  selectedText: string;
  startOffset: number;
  endOffset: number;
  comment: string;
  timestamp: string;
  documentId?: string;
}

export interface ReviewMetrics {
  word_count?: number;
  prose_density?: number;
  quality_passed?: boolean;
  banned_patterns_found?: string[];
  prose_quality_pass_1?: Record<string, unknown>;
  prose_quality_pass_2?: Record<string, unknown>;
  compliance_result?: Record<string, unknown>;
}

export interface DocumentSection {
  id: string;
  label: string;
  content: string;
}

export interface ReviewPayload {
  document: Record<string, string>;
  metrics: ReviewMetrics;
  recipe: string;
  project_id: string;
  project_name: string;
  review_round: number;
  current_step: string;
}

export interface VSItem {
  content: string;
  probability: number;
  metadata: {
    label?: "conventional" | "novel" | "exploratory";
    quality_score?: number | null;
    p_raw?: number;
    repairs?: string[];
    [key: string]: unknown;
  };
}

export interface VSDistribution {
  distribution_id: string;
  items: VSItem[];
  model: string;
  phase: string;
  k: number;
  tau: number;
  sum_probability: number;
  tau_relaxed: boolean;
  num_filtered: number;
  created_at: string;
}

export interface ReviewPayloadWithVS extends ReviewPayload {
  vs_distributions?: Record<string, VSDistribution>;
}

export interface ResumeValue {
  decision: "approved" | "revision" | "rejected";
  comments: ReviewComment[];
  feedback?: string;
}
