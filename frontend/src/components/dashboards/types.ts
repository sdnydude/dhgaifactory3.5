export type PromVectorResult = {
  metric: Record<string, string>;
  value: [number, string];
};

export type PromMatrixResult = {
  metric: Record<string, string>;
  values: [number, string][];
};

export type PromTarget = {
  labels: { job?: string; instance?: string };
  health: "up" | "down" | "unknown";
  lastScrape: string;
  scrapeUrl: string;
};

// Mirrors registry/cme_schemas.py — PipelineStatsResponse + sub-models
export interface AgentCompletionItem {
  agent: string;
  count: number;
  avg_quality: number | null;
}

export interface DocumentThroughputItem {
  type: string;
  count: number;
  avg_words: number;
  avg_quality: number | null;
}

export interface ActivePipelineItem {
  project_id: string;
  name: string;
  status: string;
  current_agent: string | null;
  progress_percent: number;
}

export interface CmePipelineStats {
  projects_by_status: Record<string, number>;
  total_projects: number;
  total_runs: number;
  total_documents: number;
  total_references: number;
  agent_completion: AgentCompletionItem[];
  document_throughput: DocumentThroughputItem[];
  avg_run_duration_sec: number | null;
  active_pipelines: ActivePipelineItem[];
}

// Mirrors registry/cme_schemas.py — ServiceHealthResponse + sub-models
export interface ServiceItem {
  name: string;
  domain: string;
}

export interface CmeServiceStats {
  service_count: number;
  services: ServiceItem[];
  db_active_connections: number;
  table_counts: Record<string, number>;
}

export interface LgTopNode {
  span_name: string;
  calls: number;
}

export interface CorrectionCategoryStats {
  category: string;
  count_7d: number;
  count_30d: number;
  count_all: number;
  most_recent: string | null;
  most_recent_message: string | null;
  repeat_flag: boolean;
  trend: string;
}

export interface CorrectionStats {
  total_7d: number;
  total_30d: number;
  total_all: number;
  categories: CorrectionCategoryStats[];
  active_repeats: string[];
  top_pattern: string | null;
  top_pattern_count: number | null;
  top_pattern_example: string | null;
}

export interface FeedbackLoopTypeStats {
  type: string;
  count_7d: number;
  count_total: number;
  last_capture: string | null;
}

export interface FeedbackLoopHealth {
  status: string;
  healthy_types: number;
  total_types: number;
  types: FeedbackLoopTypeStats[];
}

export interface DeferredItemStats {
  total: number;
  by_status: Record<string, number>;
  by_priority: Record<string, number>;
  by_category: Record<string, number>;
  age_histogram: Record<string, number>;
  stale_candidates: number;
}

export interface Telemetry {
  targets: PromTarget[] | null;
  alertsFiring: number | null;

  regReqRate: number | null;
  regErrRate: number | null;
  regLatencyP95: number | null;

  pgConnections: number | null;
  pgCacheHit: number | null;
  pgUp: number | null;

  nodeLoad1: number | null;
  nodeMemAvailPct: number | null;
  promUptime: number | null;

  lgCalls15m: number | null;
  lgLatencyP95: number | null;
  lgActiveNodes: number | null;
  lgTopNodes: LgTopNode[] | null;
  lgCallsSpark: { v: number }[];

  cmePipeline: CmePipelineStats | null;
  cmeServices: CmeServiceStats | null;

  regReqRateSpark: { v: number }[];
  regLatencySpark: { v: number }[];
  nodeLoadSpark: { v: number }[];

  correctionStats: CorrectionStats | null;
  feedbackHealth: FeedbackLoopHealth | null;
  deferredStats: DeferredItemStats | null;

  lastUpdated: Date | null;
  reachable: boolean;
}
