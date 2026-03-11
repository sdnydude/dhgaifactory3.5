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

export interface ResumeValue {
  decision: "approved" | "revision" | "rejected";
  comments: ReviewComment[];
  feedback?: string;
}
