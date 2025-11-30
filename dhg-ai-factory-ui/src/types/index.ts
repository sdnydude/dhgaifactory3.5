// DHG AI Factory - TypeScript Type Definitions
// Version: 1.0
// Date: November 30, 2025

// ============================================================================
// AGENT TYPES
// ============================================================================

export type AgentId = 
  | 'orchestrator' 
  | 'research' 
  | 'medical_llm' 
  | 'curriculum' 
  | 'outcomes' 
  | 'competitor_intel' 
  | 'qa_compliance';

export type AgentStatus = 
  | 'idle' 
  | 'working' 
  | 'waiting' 
  | 'complete' 
  | 'error' 
  | 'cancelled';

export interface AgentConfig {
  id: AgentId;
  name: string;
  color: string;
  icon: string;
}

export const AGENT_CONFIGS: Record<AgentId, AgentConfig> = {
  orchestrator: {
    id: 'orchestrator',
    name: 'Orchestrator',
    color: '#0066CC',
    icon: '🎯'
  },
  research: {
    id: 'research',
    name: 'Research Agent',
    color: '#059669',
    icon: '🔬'
  },
  medical_llm: {
    id: 'medical_llm',
    name: 'Medical LLM',
    color: '#7C3AED',
    icon: '🏥'
  },
  curriculum: {
    id: 'curriculum',
    name: 'Curriculum Agent',
    color: '#EA580C',
    icon: '📚'
  },
  outcomes: {
    id: 'outcomes',
    name: 'Outcomes Agent',
    color: '#DB2777',
    icon: '📊'
  },
  competitor_intel: {
    id: 'competitor_intel',
    name: 'Competitor Intel',
    color: '#0891B2',
    icon: '🔍'
  },
  qa_compliance: {
    id: 'qa_compliance',
    name: 'QA/Compliance',
    color: '#DC2626',
    icon: '✓'
  }
};

// ============================================================================
// COMPLIANCE & TASK TYPES
// ============================================================================

export type ComplianceMode = 'auto' | 'cme' | 'non_cme';

export type MooreLevel = '1' | '2' | '3a' | '3b' | '4' | '5' | '6' | '7';

export type TaskType = 
  | 'needs_assessment' 
  | 'curriculum' 
  | 'competitor_analysis' 
  | 'outcomes_analysis'
  | 'grant_development';

export interface TaskTypeConfig {
  id: TaskType;
  name: string;
  description: string;
  estimatedDuration: number; // seconds
  requiredAgents: AgentId[];
}

export const TASK_TYPES: Record<TaskType, TaskTypeConfig> = {
  needs_assessment: {
    id: 'needs_assessment',
    name: 'Needs Assessment',
    description: 'Educational gap analysis for CME content',
    estimatedDuration: 60,
    requiredAgents: ['orchestrator', 'research', 'medical_llm', 'qa_compliance']
  },
  curriculum: {
    id: 'curriculum',
    name: 'Curriculum Development',
    description: 'Full curriculum with learning objectives',
    estimatedDuration: 120,
    requiredAgents: ['orchestrator', 'research', 'curriculum', 'medical_llm', 'qa_compliance']
  },
  competitor_analysis: {
    id: 'competitor_analysis',
    name: 'Competitor Analysis',
    description: 'Market intelligence on competing programs',
    estimatedDuration: 90,
    requiredAgents: ['orchestrator', 'competitor_intel', 'research', 'qa_compliance']
  },
  outcomes_analysis: {
    id: 'outcomes_analysis',
    name: 'Outcomes Analysis',
    description: 'Measure and analyze educational outcomes',
    estimatedDuration: 75,
    requiredAgents: ['orchestrator', 'outcomes', 'research', 'qa_compliance']
  },
  grant_development: {
    id: 'grant_development',
    name: 'Grant Development',
    description: 'Medical education grant proposal development',
    estimatedDuration: 180,
    requiredAgents: ['orchestrator', 'research', 'medical_llm', 'curriculum', 'outcomes', 'qa_compliance']
  }
};

// ============================================================================
// REQUEST TYPES
// ============================================================================

export interface CMERequest {
  task_type: TaskType;
  topic: string;
  compliance_mode: ComplianceMode;
  target_audience: string;
  funder?: string;
  moore_levels?: MooreLevel[];
  word_count_target?: number;
  reference_count?: number;
  additional_context?: Record<string, unknown>;
}

export interface RequestStatus {
  request_id: string;
  status: 'pending' | 'processing' | 'complete' | 'failed' | 'cancelled';
  created_at: string;
  updated_at: string;
  estimated_duration?: number;
  progress: number;
  current_agent?: AgentId;
}

// ============================================================================
// WEBSOCKET EVENT TYPES
// ============================================================================

export interface WebSocketEvent<T = unknown> {
  type: string;
  id: string;
  timestamp: string;
  session_id: string;
  request_id?: string;
  correlation_id?: string;
  payload: T;
  meta?: {
    agent_id?: AgentId;
    sequence?: number;
    retry_count?: number;
  };
}

// Connection Events
export interface ConnectionInitPayload {
  client_id: string;
  token: string;
  client_version: string;
  capabilities: string[];
}

export interface ConnectionAckPayload {
  session_id: string;
  server_version: string;
  heartbeat_interval: number;
  agents_available: AgentId[];
}

// Agent Events
export interface AgentStatusPayload {
  agent_id: AgentId;
  agent_name: string;
  status: AgentStatus;
  previous_status?: AgentStatus;
  task_description?: string;
  progress?: {
    current: number;
    total: number;
    unit: 'percent' | 'items' | 'steps';
  };
}

export interface AgentProgressPayload {
  agent_id: AgentId;
  progress: {
    current: number;
    total: number;
    unit: 'percent' | 'items' | 'steps';
  };
  message: string;
  details?: Record<string, unknown>;
}

export interface AgentLogPayload {
  agent_id: AgentId;
  level: 'debug' | 'info' | 'warning' | 'error';
  message: string;
  data?: Record<string, unknown>;
}

// Content Events
export interface ContentChunkPayload {
  chunk_index: number;
  content: string;
  section: string;
  is_final: boolean;
  agent_id: AgentId;
}

export interface ContentCompletePayload {
  content_id: string;
  title: string;
  format: 'markdown' | 'html' | 'json';
  content: string;
  metadata: {
    word_count: number;
    reference_count: number;
    sections: string[];
    generation_time_ms: number;
    compliance_mode: ComplianceMode;
    moore_levels_addressed?: MooreLevel[];
  };
}

// Validation Events
export interface ValidationIssue {
  code: string;
  message: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  section?: string;
  line?: number;
}

export interface ValidationCheckResult {
  status: 'passed' | 'failed' | 'warning';
  score: number;
  details?: Record<string, unknown>;
}

export interface ValidationCompletePayload {
  content_id: string;
  overall_status: 'passed' | 'failed' | 'warning';
  checks: Record<string, ValidationCheckResult>;
  violations: ValidationIssue[];
  warnings: ValidationIssue[];
  validation_time_ms: number;
}

// Chat Events
export interface ChatMessagePayload {
  content: string;
  request_id?: string;
  attachments?: string[];
}

export interface ChatResponsePayload {
  content: string;
  agent_id: AgentId;
  suggestions?: string[];
}

// Error Events
export interface ErrorPayload {
  code: string;
  message: string;
  severity: 'warning' | 'error' | 'critical';
  recoverable: boolean;
  agent_id?: AgentId;
  details?: Record<string, unknown>;
}

// ============================================================================
// APPLICATION STATE TYPES
// ============================================================================

export interface AgentState {
  id: AgentId;
  status: AgentStatus;
  taskDescription?: string;
  progress: number;
  logs: AgentLogEntry[];
  lastUpdated: string;
}

export interface AgentLogEntry {
  id: string;
  timestamp: string;
  level: 'debug' | 'info' | 'warning' | 'error';
  message: string;
  data?: Record<string, unknown>;
}

export interface ChatMessage {
  id: string;
  timestamp: string;
  role: 'user' | 'agent';
  agent_id?: AgentId;
  content: string;
  suggestions?: string[];
}

export interface GeneratedContent {
  id: string;
  request_id: string;
  title: string;
  content: string;
  format: 'markdown' | 'html' | 'json';
  sections: ContentSection[];
  metadata: ContentMetadata;
  validation?: ValidationResult;
  created_at: string;
}

export interface ContentSection {
  id: string;
  name: string;
  content: string;
  word_count: number;
  references: string[];
}

export interface ContentMetadata {
  word_count: number;
  reference_count: number;
  generation_time_ms: number;
  compliance_mode: ComplianceMode;
  moore_levels?: MooreLevel[];
  target_audience: string;
  topic: string;
}

export interface ValidationResult {
  status: 'passed' | 'failed' | 'warning';
  checks: Record<string, ValidationCheckResult>;
  violations: ValidationIssue[];
  warnings: ValidationIssue[];
  validated_at: string;
}

// ============================================================================
// UI STATE TYPES
// ============================================================================

export interface UIState {
  leftPanelOpen: boolean;
  rightPanelOpen: boolean;
  leftPanelWidth: number;
  rightPanelWidth: number;
  activeView: 'dashboard' | 'generate' | 'history' | 'settings' | 'admin';
  theme: 'light' | 'dark' | 'system';
  compactMode: boolean;
}

export interface RequestHistoryItem {
  id: string;
  task_type: TaskType;
  topic: string;
  compliance_mode: ComplianceMode;
  status: 'complete' | 'failed' | 'processing';
  created_at: string;
  word_count?: number;
  reference_count?: number;
  validation_status?: 'passed' | 'failed' | 'warning';
}

// ============================================================================
// FORM TYPES
// ============================================================================

export interface RequestFormData {
  task_type: TaskType;
  topic: string;
  compliance_mode: ComplianceMode;
  target_audience: string;
  funder: string;
  moore_levels: MooreLevel[];
  word_count_target: number;
  reference_count: number;
  additional_context: string; // JSON string
}

export interface RequestFormErrors {
  task_type?: string;
  topic?: string;
  compliance_mode?: string;
  target_audience?: string;
  funder?: string;
  moore_levels?: string;
  word_count_target?: string;
  reference_count?: string;
  additional_context?: string;
}

// ============================================================================
// ZUSTAND STORE TYPES
// ============================================================================

export interface AppState {
  // Connection
  connected: boolean;
  sessionId: string | null;
  
  // Agents
  agents: Record<AgentId, AgentState>;
  
  // Current Request
  currentRequest: RequestStatus | null;
  currentContent: GeneratedContent | null;
  
  // Chat
  messages: ChatMessage[];
  isTyping: boolean;
  
  // History
  history: RequestHistoryItem[];
  
  // UI
  ui: UIState;
}

export interface AppActions {
  // Connection
  setConnected: (connected: boolean) => void;
  setSessionId: (sessionId: string) => void;
  
  // Agents
  updateAgentStatus: (payload: AgentStatusPayload) => void;
  addAgentLog: (agentId: AgentId, log: AgentLogEntry) => void;
  clearAgentLogs: (agentId: AgentId) => void;
  
  // Request
  setCurrentRequest: (request: RequestStatus | null) => void;
  updateRequestProgress: (progress: number) => void;
  
  // Content
  appendContentChunk: (chunk: ContentChunkPayload) => void;
  setCurrentContent: (content: GeneratedContent | null) => void;
  setValidationResult: (result: ValidationResult) => void;
  
  // Chat
  addMessage: (message: ChatMessage) => void;
  setTyping: (isTyping: boolean) => void;
  clearMessages: () => void;
  
  // History
  addToHistory: (item: RequestHistoryItem) => void;
  loadHistory: (items: RequestHistoryItem[]) => void;
  
  // UI
  toggleLeftPanel: () => void;
  toggleRightPanel: () => void;
  setLeftPanelWidth: (width: number) => void;
  setRightPanelWidth: (width: number) => void;
  setActiveView: (view: UIState['activeView']) => void;
  setTheme: (theme: UIState['theme']) => void;
}

export type AppStore = AppState & AppActions;
