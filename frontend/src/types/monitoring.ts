// Stats types — match session-logger Pydantic models exactly

export interface StatsOverview {
  total_sessions: number;
  total_chunks: number;
  total_concepts: number;
  total_edges: number;
  avg_chunks_per_session: number;
  embedding_coverage_pct: number;
  earliest_session: string | null;
  latest_session: string | null;
}

export interface DailySessionCount {
  date: string;
  session_count: number;
}

export interface DailyStats {
  days: DailySessionCount[];
  period_start: string | null;
  period_end: string | null;
}

export interface ConceptRanking {
  name: string;
  node_type: string;
  edge_count: number;
}

export interface NodeTypeBreakdown {
  node_type: string;
  count: number;
}

export interface ConceptStats {
  top_concepts: ConceptRanking[];
  node_type_breakdown: NodeTypeBreakdown[];
  total_nodes: number;
  total_edges: number;
}

// Service health

export interface ServiceHealth {
  name: string;
  port: number;
  status: "healthy" | "degraded" | "down";
  responseMs: number;
  description: string;
}

export interface SessionLoggerHealth {
  status: string;
  database: string;
  ollama: string;
  embeddings: string;
  summarization: string;
}

// Alertmanager

export interface AlertmanagerStatus {
  state: string;
}

export interface AlertmanagerAlert {
  status: AlertmanagerStatus;
  labels: Record<string, string>;
  annotations: Record<string, string>;
  startsAt: string;
  endsAt: string;
  generatorURL?: string;
}

// Prometheus metrics (parsed)

export interface OperationCounter {
  operation: string;
  count: number;
}

export interface LatencyPercentiles {
  p50: number;
  p95: number;
  p99: number;
}

export interface ParsedMetrics {
  operations: OperationCounter[];
  latency: LatencyPercentiles;
  totalErrors: number;
}
